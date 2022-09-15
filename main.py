import PyPDF2, json, math, pprint
import itertools as itt
from time import perf_counter

EVENTS = [
    "4x50fr",
    "4x100fr",
    "4x200fr",
    "4x50mr",
    "4x100mr",
    ]
INDIVIDUAL_EVENTS = [
    "50fr",
    "100fr",
    "200fr",
    "50ba",
    "100ba",
    "50br",
    "100br",
    "50fl",
    "100fl"
]
FREE_RELAYS = {
    "4x50fr":"50fr",
    "4x100fr":"100fr",
    "4x200fr":"200fr",
}
RELAY_RECORDS_MEN = {
    "4x50fr":"1:14.08",
    "4x100fr":"2:44.31",
    "4x200fr":"6:03.89",
    "4x50mr":"1:21.13",
    "4x100mr":"2:59.22",
}

RELAY_RECORDS_WOMEN = {
    "4x50fr":"1:24.47",
    "4x100fr":"3:06.91",
    "4x200fr":"6:45.91",
    "4x50mr":"1:31.81",
    "4x100mr":"3:22.34",
}

TEAM_NAMES = {
        0 : "A Team",
        1 : "B Team",
        2 : "C Team",
    }

def convert_time_to_seconds(time):
    '''
    Converts a time in the format "XX:XX.XX" to the number of seconds.
    '''
    seconds = 0
    if ':' in time:
        colon_index = time.index(':')
        minutes = int(time[:colon_index])
        seconds += minutes * 60
        time = time[colon_index + 1:]
        seconds += float(time)
    else:
        seconds = float(time)
    return round(seconds,2)

def calculate_points(event, swim_time, gender):
    '''
    Returns the points using Swimcloud's method and the NCAA records as base times:
    https://support.swimcloud.com/hc/en-us/articles/360052519314-How-are-performance-rankings-calculated-
    '''
    base_time = RELAY_RECORDS_MEN[event] if gender == "male" else RELAY_RECORDS_WOMEN[event]
    base_time = convert_time_to_seconds(base_time)
    return round(1000 * math.pow(base_time/swim_time,3))

def extract_rankings(file_name, team_name):
    '''
    Returns an ordered array of times for an event.

    Parameters
    ----------
    file_name : str
        The name of the pdf file to extract times from.

    team_name : str
        The name of the team where the times are from.

    Returns
    -------
    rankings : arr of tuples
        An ordered array of tuples, each with a length of 2. The formatting of the tuples is
        (``full_name``, ``time``), where ``full_name`` and ``time`` are both strings. Array is
        ordered by ``time``, from fastest to slowest.
    '''
    data = read_pdf(file_name)

    start_word = "Time"
    start_index = data.index(start_word)
    times = data[start_index + len(start_word):]
    school_index = times.index(team_name)
    times = times[:school_index]
    
    time_array = times.split('.')
    for i in range(1,len(time_array)):
        fractional_seconds = time_array[i][0:2]
        time_array[i-1] += '.' + fractional_seconds
        time_array[i] = time_array[i][2:]
    
    rankings = []
    for i in range(len(time_array)-1):
        time_data = time_array[i]
        #length of the ranking in front of name
        ranking_length = len(str(i+1))
        time_data = time_data[ranking_length:]
        name = ""
        name_index = 0
        for j in range(len(time_data)):
            char = time_data[j]
            if not char.isdigit():
                name += char
            else:
                name_index = j
                break
        time = time_data[name_index:]
        rankings.append((name, time))

    return rankings

def read_pdf(file_name):
    '''
    Reads a pdf and returns the extracted text.
    '''
    text = ""
    with open(file_name, "rb") as pdfFileObj:
        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
        pageObj = pdfReader.getPage(0)
        text = pageObj.extractText()
    return text

def generate_indices(length):
    '''
    Returns an array of all 0's with length ``length``.
    '''
    indices = []
    for _ in range(length):
        indices.append(0)
    return indices

def new_2d_array(length):
    '''
    Returns an empty 2-d array with length ``length``.
    '''
    permutation = []
    for _ in range(length):
        permutation.append([])
    return permutation

def generate_event_combinations(swimmer_events, relays_per_swimmer, restricted_swimmers):
    '''
    For every swimmer that exceeds ``relays_per_swimmer``, returns all possible combinations of the 
    indices of the relays that they can swim under the limit.

    Parameters
    ----------
    swimmer_events : dict
        key : swimmer name
        value : array of indices of the relays the swimmer is apart of
        A dictionary describing the indices of the relays a swimmer will swim. For each index ``i`` in the array,
        the swimmer is set to swim the ``i``th relay in ``EVENTS``.
    
    relays_per_swimmer : int
        The maximum number of relays each swimmer can swim.

    Returns
    -------
    swimmer_combinations : dict
        key : swimmer name
        value : 2-d array of ints
            The array contains the different combinations of the relays the swimmer can swim.
            Each sub-array contains the indices of the relays that a swimmer can take part in and
            0.
            is restricted to a length of ``relays_per_swimmer``.
    '''
    swimmer_combinations = {}
    # find swimmers who exceeded relay limit
    for swimmer, events in swimmer_events.items():
        limit = restricted_swimmers[swimmer] if swimmer in restricted_swimmers.keys() else relays_per_swimmer
        if len(events) > limit:
            combinations = list(itt.combinations(events, limit))
            swimmer_combinations[swimmer] = combinations
    return swimmer_combinations

def remove_swimmers_from_rankings(rankings, excluded_swimmers):
    '''
    Removes a swimmer from the rankings.
    '''
    modified_rankings = []
    for stroke_rankings in rankings:
        modified_rankings.append(stroke_rankings.copy())
    
    for i, stroke_rankings in enumerate(rankings):
        for pair in stroke_rankings:
            name = pair[0]
            if name in excluded_swimmers:
                modified_rankings[i].remove(pair)
    return modified_rankings

def medley_relay_repeats(rankings, team, excluded_swimmers):
    new_team = team.copy()
    name_count = {}

    possible_teams = []

    for i, pair in enumerate(team):
        stroke_rankings = rankings[i]
        if pair is None:
            if len(stroke_rankings) == 0:
                return []
            new_team[i] = stroke_rankings[0]
        name = new_team[i][0]
        if name not in name_count.keys():
            name_count[name] = [i]
        else:
            name_count[name].append(i)

    for name in name_count.keys():
        indices = name_count[name]
        if len(indices) > 1:
            # swimmer is first for multiple legs of the relay
            temp_rankings = remove_swimmers_from_rankings(rankings, excluded_swimmers + [name])
            combinations = list(itt.combinations(indices, len(indices)-1))
            for combination in combinations:
                temp_team = new_team.copy()
                for index in combination:
                    temp_team[index] = None
                possible_teams += medley_relay_repeats(temp_rankings, temp_team, excluded_swimmers)

    if len(possible_teams) == 0:
        possible_teams.append(new_team)

    return possible_teams

def medley_relay_teams(rankings, excluded_swimmers):
    '''
    rankings : 2-d array, length 4
    '''
    modified_rankings = remove_swimmers_from_rankings(rankings, excluded_swimmers)
    teams = []

    possible_teams = medley_relay_repeats(modified_rankings, [None, None, None, None], excluded_swimmers)

    best_time = 0
    best_team = []
    for team in possible_teams:
        total_time = 0
        for pair in team:
            time = convert_time_to_seconds(pair[1])
            total_time += time
        if best_team == [] or total_time < best_time:
            best_team = team
            best_time = total_time

    teams.append(best_team)

    to_exclude = []
    for pair in teams[-1]:
        name = pair[0]
        to_exclude.append(name)
    
    modified_rankings = remove_swimmers_from_rankings(modified_rankings, to_exclude)
    
    return teams

def free_relay_teams(rankings, excluded_swimmers):
    '''
    Returns the best free relay team(s) for an event.

    Parameters
    ----------
    rankings : arr of tuples
        An ordered array of tuples, each tuple containing the full name of the swimmer
        along with their time. See extract_rankings for more details.
    
    excluded_swimmers : arr of strings
        An array of names to be excluded from the relay teams.

    relays_per_event : int
        The number of relay teams to generate lineups for.

    Returns
    -------
    teams : 2-d array of tuples
        An 2-d array with a length of ``relays_per_event``. Each sub-array represents one 
        relay team and contains 4 tuples in the format of (full name, time) representing 
        the swimmers on each relay.
    '''
    teams = []
    modified_rankings = rankings.copy()
    for pair in rankings:
        name = pair[0]
        if name in excluded_swimmers:
            modified_rankings.remove(pair)

    team = []
    if len(modified_rankings) >= 4:
        for i in range(4):
            team.append(modified_rankings[i])
    teams.append(team)

    return teams

def generate_lineup(all_rankings, excluded_swimmers_2d):
    '''
    Returns a lineup for all relays.

    Parameters
    ----------
    all_rankings : dict
        key : event name
        value : array of tuples with rankings
        A dictionary of rankings for each event. See extract_rankings for more details.

    excluded_swimmers_2d : 2-d array of strings
        A 2-d array of strings with the same length as ``EVENTS``. The sub-array at the nth
        index is an array of swimmer names to be excluded from the relay at the nth index of
        ``EVENTS``.
    
    Returns
    -------
    swimmer_events : dict
        key : swimmer name
        value : array of indices of the relays the swimmer is apart of
        A dictionary describing which relays a swimmer will swim. For each index i in the array,
        the swimmer will be swimming the ith relay in ``EVENTS``.

    relay_groups : dict
        key : event
        value : 2-d array with a length of ``relays_per_event``.
        A dictionary describing the relay teams for each event. See ``relay_teams`` for more details.       
    '''
    relay_groups = {}
    swimmer_events = {}
    
    for relay_name in EVENTS:
        event_index = EVENTS.index(relay_name)
        if relay_name in FREE_RELAYS.keys():
            #free relays
            individual_event_name = FREE_RELAYS[relay_name]
            rankings = all_rankings[individual_event_name]
            relay_group = free_relay_teams(rankings, excluded_swimmers_2d[event_index])
            relay_groups[relay_name] = relay_group
            for relay_team in relay_group:
                for pair in relay_team:
                    name = pair[0]
                    if name not in swimmer_events.keys():
                        swimmer_events[name] = [event_index]
                    else:
                        swimmer_events[name].append(event_index)
        else:
            #medley relays
            medley_rankings = []
            if relay_name == "4x50mr":
                medley_rankings.append(all_rankings["50ba"])
                medley_rankings.append(all_rankings["50br"])
                medley_rankings.append(all_rankings["50fl"])
                medley_rankings.append(all_rankings["50fr"])
            else:
                medley_rankings.append(all_rankings["100ba"])
                medley_rankings.append(all_rankings["100br"])
                medley_rankings.append(all_rankings["100fl"])
                medley_rankings.append(all_rankings["100fr"])
            
            relay_group = medley_relay_teams(medley_rankings, excluded_swimmers_2d[event_index])

            relay_groups[relay_name] = relay_group
            for relay_team in relay_group:
                for pair in relay_team:
                    name = pair[0]
                    if name not in swimmer_events.keys():
                        swimmer_events[name] = [event_index]
                    else:
                        swimmer_events[name].append(event_index)
    return swimmer_events, relay_groups

def generate_all_lineups(prev_event_combinations, rankings, relays_per_swimmer, top_events, restricted_swimmers, all_event_combinations):
    '''
    Returns a list of all possible lineups.

    Parameters
    ----------
    prev_event_combinations : dict
        key : swimmer name
        value : 2-d array of ints
            Each sub-array contains the indices of the relays that a swimmer can take part in and
            is restricted to a length of ``relays_per_swimmer``. Each sub-array represents a possible
            lineup for the relays that the swimmer can take part in.
    
    rankings : dict
        key : event name
        value : array of tuples with rankings
        A dictionary of rankings for each event. See extract_rankings for more details.

    relays_per_swimmer : int
        The maximum number of relays each swimmer can swim.

    relays_per_event : int
        The number of relay teams for each event.

    Returns
    -------
    lineups : arr
        An array of tuples. Each tuple has the format of (swimmer_events, relay_groups) returned by ``generate_lineup``.
    '''
    
    # ``forbidden_swimmer_arrays`` is a 2-d array of arrays, each called ``forbidden_events``
    # Every ``forbidden_events`` is an array with the same length as ``EVENTS``. If the ``i``th index
    # of ``forbidden_events`` is the swimmer's name, then the swimmer cannot swim the ``i``th event.
    
    forbidden_swimmer_arrays = []
    
    updated_event_combinations = all_event_combinations.copy()

    # convert swimmer_combinations to string form
    for swimmer, combinations in prev_event_combinations.items():
        combination_arrays = []
        for combination in combinations:
            combination_array = [""] * len(EVENTS)
            for i in range(len(EVENTS)):
                if i not in combination:
                    combination_array[i] = swimmer
            combination_arrays.append(combination_array)
        forbidden_swimmer_arrays.append(combination_arrays)

    indices = generate_indices(len(forbidden_swimmer_arrays))

    # ``forbidden_swimmer_permutations`` is an array of 2-d arrays, each called ``permutation``
    #  every ``permutation`` is a 2-d array with the same length as ``EVENTS``. The ``i``th index of ``permutation``
    #  contains the swimmers not allowed to swim the ``i``th event.
    forbidden_swimmers_permutations = []

    # generate permutations
    while len(forbidden_swimmer_arrays) > 0 and indices[-1] < len(forbidden_swimmer_arrays[-1]):
        start_index = indices[0]
        first_combination = forbidden_swimmer_arrays[0][start_index]

        # initialize permutation
        forbidden_swimmers = []
        for c in first_combination:
            exceeded = []
            if c != '':
                exceeded.append(c)
            forbidden_swimmers.append(exceeded)
        
        # add other names to permutation
        for i in range(1,len(forbidden_swimmer_arrays)):
            index = indices[i]
            combination = forbidden_swimmer_arrays[i][index]
            for j,c in enumerate(combination):
                if c != '':
                    forbidden_swimmers[j].append(c)
        
        forbidden_swimmers_permutations.append(forbidden_swimmers)
        
        # update indices
        indices[0] += 1
        for i in range(len(indices)-1):
            if indices[i] == len(forbidden_swimmer_arrays[i]):
                indices[i] = 0
                indices[i+1] += 1
    
    
    lineups = []
    if len(forbidden_swimmers_permutations) == 0:
        forbidden_swimmers_permutations.append(new_2d_array(len(EVENTS)))


    for i, forbidden_swimmers in enumerate(forbidden_swimmers_permutations):
        # count += 1
        swimmer_events, relay_groups = generate_lineup(rankings, forbidden_swimmers)
        event_combinations = generate_event_combinations(swimmer_events, relays_per_swimmer, restricted_swimmers)

        not_optimal = False
        # Check if lineup is optimal:
        # if a top swimmer is not swimming their minimum number of events, the lineup is not optimal
        for name, minimum_events in top_events.items():
            if name not in swimmer_events:
                not_optimal = True
                break
            current_number_of_events = len(swimmer_events[name])
            if current_number_of_events < minimum_events:
                not_optimal = True
                break
        if not_optimal:
            continue

        if len(event_combinations.keys()) > 0:
            # At least one swimmer is signed up to swim more than ``relays_per_swimmer`` relays.
            for swimmer, combinations in prev_event_combinations.items():
                if swimmer not in event_combinations.keys():
                    event_combinations[swimmer] = combinations
            if event_combinations in updated_event_combinations:
                continue
            updated_event_combinations.append(event_combinations)
            generated_lineups, new_event_combinations = generate_all_lineups(event_combinations, rankings, relays_per_swimmer, top_events, restricted_swimmers, updated_event_combinations)
            lineups += generated_lineups
            updated_event_combinations = new_event_combinations

        else:
            lineups.append((swimmer_events, relay_groups))
    
    return lineups, updated_event_combinations

def write_rankings(rankings):
    with open('rankings.txt','w') as f:
        for event, list in rankings.items():
            f.write(event+'\n')
            f.write(str(list)+'\n')

def best_lineup(lineups, gender):
    best = None
    best_points = 0

    #find best lineup
    for lineup in lineups:
        total_points = 0
        relay_groups = lineup[1]
        for event, relay_group in relay_groups.items():
            total_time = 0
            #hard-coded for one relay team per event
            if len(relay_group) == 0:
                continue
            relay_team = relay_group[0]
            for pair in relay_team:
                time = convert_time_to_seconds(pair[1])
                total_time += time
            if total_time == 0:
                continue
            total_points += calculate_points(event, total_time, gender)
        total_points /= len(EVENTS)
        if best == None or total_points > best_points:
            best = lineup
            best_points = total_points
    return best, best_points

def swimmer_minimum_events(all_rankings, relays_per_swimmer, event_combinations):
    top_swimmers = {}

    mr_50 = ["50fr", "50ba", "50br", "50fl"]
    mr_100 = ["100fr","100ba","100br","100fl"]

    for i, event in enumerate(EVENTS):
        if event[-2:] == "mr":
            individual_events = mr_50 if event == "4x50mr" else mr_100
            for individual_event in individual_events:
                rankings = all_rankings[individual_event]
                for pair in rankings:
                    name = pair[0]
                    # swimmer already swimming this event
                    if name in event_combinations and i not in event_combinations[name][0]:
                        continue
                    if name not in top_swimmers.keys():
                        top_swimmers[name] = 1
                    else:
                        top_swimmers[name] += 1
                    break
        else:
            individual_event = FREE_RELAYS[event]
            rankings = all_rankings[individual_event]
            swimmers_added = 0
            for pair in rankings:
                if swimmers_added == 4:
                    break
                name = pair[0]
                # swimmer already swimming this event

                if name in event_combinations and i not in event_combinations[name][0]:
                    continue
                if name not in top_swimmers.keys():
                    top_swimmers[name] = 1
                else:
                    top_swimmers[name] += 1
                swimmers_added += 1
    
    # make sure each swimmer is swimming under limit of relays
    # ``top_swimmers`` should now contain the minimum relays each swimmer should be apart of for each swimmer in the dict
    for name, events in top_swimmers.items():
        limit = relays_per_swimmer
        if name in event_combinations:
            limit -=  len(EVENTS) - len(event_combinations[name][0])
        top_swimmers[name] = min(events, limit)

    return top_swimmers

def extract_all_rankings(school_name, gender):
    all_rankings = {}
    for event in INDIVIDUAL_EVENTS:
        all_rankings[event] = extract_rankings(f"times/{gender}/{school_name} - Top Times - {event}.pdf", school_name)

    write_rankings(all_rankings)
    return all_rankings

def remove_swimmers_from_all_rankings(rankings, excluded_swimmers):
    modified_rankings = {}

    for event, stroke_rankings in rankings.items():
        modified_rankings[event] = stroke_rankings.copy()
        for pair in stroke_rankings:
            name = pair[0]
            if name in excluded_swimmers:
                modified_rankings[event].remove(pair)
    
    return modified_rankings

def find_best_lineup(relays_per_event, relays_per_swimmer, school_name, gender):
    all_rankings = extract_all_rankings(school_name, gender)

    complete_lineup = {
        "Maximum Relays Per Event": relays_per_event,
        "Maximum Relays Per Swimmer": relays_per_swimmer,
    }

    modified_rankings = all_rankings.copy()
    event_combinations = {}
    restricted_swimmers = {}

    total_event_indices = {}

    for i in range(relays_per_event):
        # all_event_combinations.clear()
        t0 = perf_counter()
        team_name = TEAM_NAMES[i]
        print(f"Finding best lineup for {team_name}...")

        minimum_events = swimmer_minimum_events(modified_rankings, relays_per_swimmer, event_combinations)

        lineups, _ = generate_all_lineups(event_combinations, modified_rankings, relays_per_swimmer, minimum_events, restricted_swimmers, [])
        lineup, points = best_lineup(lineups, gender)
        swimmer_events = lineup[0]
        relay_teams = lineup[1]
        complete_lineup[team_name] = {
            "Average Points Per Relay": points,
            "Lineup": relay_teams,
        }

        # reset rankings based on previous relay teams
        maxed_swimmers = []
        event_combinations.clear()
        restricted_swimmers.clear()

        for swimmer, event_lineup in swimmer_events.items():
            prev_events = []
            if swimmer in total_event_indices.keys():
                prev_events = total_event_indices[swimmer]
            if len(prev_events) + len(event_lineup) == relays_per_swimmer:
                # maxed out relays
                maxed_swimmers.append(swimmer)
            else:
                available_relays = []
                for j in range(len(EVENTS)):
                    if j not in event_lineup:
                        available_relays.append(j)
                event_combinations[swimmer] = [available_relays]
                restricted_swimmers[swimmer] = relays_per_swimmer - len(event_lineup)
            total_event_indices[swimmer] = prev_events + event_lineup

        modified_rankings = remove_swimmers_from_all_rankings(modified_rankings, maxed_swimmers)

        print(f"Finished in {round(perf_counter() - t0,2)} seconds.")

    with open(f'lineup_{relays_per_event}_rpe_{relays_per_swimmer}_rps_{gender}.json','w') as f:
        json.dump(complete_lineup,f,indent = 2)

    print(f"Finished.")
    
def check_swimmer_limit(relays_per_event, relays_per_swimmer, gender):
    data = {}
    with open(f'lineup_{relays_per_event}_rpe_{relays_per_swimmer}_rps_{gender}.json','r') as f:
        data = json.load(f)
    swimmer_count = {}
    for team in TEAM_NAMES.values():
        if team in data.keys():
            lineup_data = data[team]
            lineup = lineup_data["Lineup"]
            for relay_group in lineup.values():
                # TODO: fix nesting index problem
                team = relay_group[0]
                for pair in team:
                    name = pair[0]
                    if name not in swimmer_count.keys():
                        swimmer_count[name] = 1
                    else:
                        swimmer_count[name] += 1
                        if swimmer_count[name] > relays_per_swimmer:
                            print(f"{name} set to swim more than {relays_per_swimmer} events.")
                            return
    print(f"All swimmers within {relays_per_swimmer} events.")
    

def main():
    school_name = "California Institute of Technology"
    gender = "female"
    relays_per_event = 3
    relays_per_swimmer = 3
    find_best_lineup(relays_per_event, relays_per_swimmer, school_name, gender)
    check_swimmer_limit(relays_per_event, relays_per_swimmer, gender)

if __name__=="__main__":
    main()