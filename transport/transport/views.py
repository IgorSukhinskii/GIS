# -*- coding: utf-8 -*-

from django.http import HttpResponse
import django.views.generic.base as base
import json
import datetime


def query(initial, final, current_time):
    from pysqlite2 import dbapi2 as sqlite3
    con = sqlite3.connect("gis.db")
    con.enable_load_extension(True)
    con.execute("select load_extension('./mod_spatialite.so')")
    con.enable_load_extension(False)
    cur = con.cursor()

    initial_point = 'POINT(%s %s)' % (initial[0], initial[1])
    final_point = 'POINT(%s %s)' % (final[0], final[1])
    cur.execute("""
        SELECT Distance(GeomFromText('%(point1)s', 4326),
                        GeomFromText('%(point2)s', 4326), 0)
    """ % {"point1": initial_point, "point2": final_point})
    direct_distance = cur.fetchone()[0]
    # first we should assemble the list of possible routes
    # we'll have at most 1 departure for each route anyway
    cur.execute("""
        SELECT r.id,
               r.number,
               r.type,
               s.id,
               s.name,
               rs.interval,
               rs.number,
               Distance(GeomFromText(s.coordinates, 4326),
                        GeomFromText('%(point1)s', 4326), 0) as distance_start,
               Distance(GeomFromText(s.coordinates, 4326),
                        GeomFromText('%(point2)s', 4326), 0) as distance_finish,
               X(GeomFromText(s.coordinates)) as lat,
               Y(GeomFromText(s.coordinates)) as lng
        FROM routes r
        JOIN routes_stops rs ON r.id = rs.route_id
        JOIN stops s ON rs.stop_id = s.id
    """ % {"point1": initial_point, "point2": final_point})
    possible_routes = {}
    for rid, rnumber, rtype, sid, sname, sinterval, snumber, distance_start, distance_finish, slat, slng in cur.fetchall():
        if rid not in possible_routes:
            possible_routes[rid] = {"id": rid, "number": rnumber, "type": rtype, "stops": {}}
        possible_routes[rid]["stops"][snumber] = {"name": sname,
                                                  "lat": slat,
                                                  "lng": slng,
                                                  "distance_start": distance_start,
                                                  "distance_finish": distance_finish,
                                                  "interval": sinterval}
    weekday = str(datetime.datetime.today().weekday() + 1)
    filtered_routes = []
    for route in possible_routes.values():
        route["stops"] = map(lambda pair: pair[1],
                             sorted(route["stops"].items(), key = lambda pair: pair[0]))
        start_stop  = min(enumerate(route["stops"]), key = lambda stop: stop[1]["distance_start"])
        finish_stop = min(enumerate(route["stops"]), key = lambda stop: stop[1]["distance_finish"])
        if start_stop[0] >= finish_stop[0]:
            continue
        route["time_to_start"] = start_stop[1]["distance_start"] / 60
        drive_time_to_start = 0
        for i in xrange(0, start_stop[0]):
            drive_time_to_start += route["stops"][i]["interval"]
        route["drive_time_to_start"] = drive_time_to_start
        cur.execute("""
            select min(time)
            from departures
            where route_id = ?
            and time > ?
            and weekdays like '%%%(weekday)s%%'
        """ % {"weekday": weekday}, (route["id"], route["time_to_start"] + current_time - drive_time_to_start))
        time_of_arrival = cur.fetchone()[0]
        if time_of_arrival is None:
            continue
        time_of_arrival += drive_time_to_start
        route["arrival"] = time_of_arrival
        route["time_to_finish"] = finish_stop[1]["distance_finish"] / 60
        time_en_route = 0
        for i in xrange(start_stop[0], finish_stop[0]):
            time_en_route += route["stops"][i]["interval"]
        route["road_time"] = time_en_route
        route["finish_time"] = route["arrival"] + route["road_time"] + route["time_to_finish"]
        route["start"] = start_stop[0]
        route["finish"] = finish_stop[0]
        filtered_routes.append(route)
    result = sorted(filtered_routes, key=lambda route: route["finish_time"])
    return result[:5]
        # result:
        # [{"number": u'81', "type": u'bus', "arrival": 945, "road_time": 17, "finish_time": 982.5, "start": 10, "finish": 20,
        #   "stops": [{"name": u'ЮУрГУ', "lat": ..., "lng": ...}, ...]}, ...]





class Frontpage(base.TemplateView):
    template_name = 'frontpage.html'


    def get(self, request, **kwargs):
        return self.render_to_response({})


class GetWay(base.View):
    def post(self, request, **kwargs):
        data = json.loads(request.POST["points"])
        time = request.POST["time"]
        print data, time
        result = query(data[0], data[1], int(time))
        return HttpResponse(json.dumps(result))