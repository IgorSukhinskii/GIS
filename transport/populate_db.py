# -*- coding: utf-8 -*-

def ParseRoutes(routes_name):
    routes = ""
    with open(routes_name, "r") as f:
        routes = f.read()
    result = []
    splittedRoutes = routes.split('\n')
    defaultRoute = {"number": u"",
             "type": u"",
             "direction": u"",
             "name": u"",
             "stops": [],
             "departures": []}
    # skipping first line
    for i in xrange(1, len(splittedRoutes), 2):
        route = defaultRoute.copy()
        splittedLine = splittedRoutes[i].split(';')
        if splittedLine[0] != "":
            route["number"] = splittedLine[0].decode('utf-8')
            defaultRoute["number"] = route["number"]
        if splittedLine[3] != "":
            route["type"] = splittedLine[3].decode('utf-8')
            defaultRoute["type"] = route["type"]
        if splittedLine[8] != "":
            route["direction"] = splittedLine[8].decode('utf-8')
            defaultRoute["direction"] = route["direction"]
        if splittedLine[10] != "":
            route["name"] = splittedLine[10].decode('utf-8')
            defaultRoute["name"] = route["name"]
        route["stops"] = map(lambda s: [s.decode('utf-8'),None], splittedLine[13].split(','))
        schedule = splittedRoutes[i + 1].split(',,')
        rawDepartures = map(int, schedule[0].split(','))
        departures = [rawDepartures[0]]
        for index, departureTime in enumerate(rawDepartures[1:]):
            departures.append(departures[index] + departureTime)
        route["departures"] = map(lambda departure: [departure, ""], departures)
        weekdays = schedule[3].split(',')
        weekdays.append("10000")
        depIndex = 0
        for j in xrange(0, len(weekdays), 2):
            currentWeekdays = weekdays[j]
            for k in xrange(int(weekdays[j+1])):
                if depIndex >= len(route["departures"]):
                    break
                route["departures"][depIndex][1] = currentWeekdays.decode('utf-8')
                depIndex += 1
        stopIntervals = map(lambda s: int(s.split(',')[0]), schedule[4:-1])
        for index, interval in enumerate(stopIntervals):
            route["stops"][index][1] = interval
        result.append(route)
    return result

def ParseStops(stops_name):
    stops = ""
    with open(stops_name, "r") as f:
        stops = f.read()
    result = []
    splittedStops = stops.split('\n')
    defaultStop = {"id": "",
                   "lat": "",
                   "lng": "",
                   "name": ""}
    for i in range(1, len(splittedStops) - 1):
        stop = defaultStop.copy()
        splittedLine = splittedStops[i].split(';')
        stop["id"] = splittedLine[0]
        stop["lat"] = splittedLine[1][:2] + "." + splittedLine[1][2:]
        stop["lng"] = splittedLine[2][:2] + "." + splittedLine[2][2:]
        if len(splittedLine) >= 5 and splittedLine[4] != "":
            stop["name"] = splittedLine[4].decode('utf-8')
            defaultStop["name"] = stop["name"]

        result.append(stop)
    return result

routes = ParseRoutes("routes.txt")
stops = ParseStops("stops.txt")

if __name__ == "__main__":
    from pysqlite2 import dbapi2 as sqlite3
    
    con = sqlite3.connect("gis.db")
    con.enable_load_extension(True)
    con.execute("select load_extension('./mod_spatialite.so')")
    con.enable_load_extension(False)
    
    con.execute('DELETE FROM stops')
    con.execute('DELETE FROM routes')
    con.execute('DELETE FROM routes_stops')
    con.execute('DELETE FROM departures')
    
    stops_to_insert = map(lambda stop: (stop["id"], 'POINT(%s %s)' % (stop["lat"], stop["lng"]), stop["name"]), stops)
    con.executemany('INSERT INTO stops VALUES (?, ?, ?)', stops_to_insert)
    
    routes_to_insert = map(lambda route: (route[0], route[1]["name"], route[1]["type"], route[1]["number"]), enumerate(routes))
    con.executemany('INSERT INTO routes VALUES (?, ?, ?, ?)', routes_to_insert)
    
    for i, route in enumerate(routes):
        for number, stop in enumerate(route["stops"]):
            con.execute('INSERT INTO routes_stops VALUES (?, ?, ?, ?)', (stop[0], i, number, stop[1]))
        for departure in route["departures"]:
            con.execute('INSERT INTO departures VALUES (?, ?, ?)', (i, departure[0], departure[1]))
    
    con.commit()
