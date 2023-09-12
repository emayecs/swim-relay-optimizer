import PyPDF2, json, math
import itertools as itt
from time import perf_counter
from collections import defaultdict

MEDLEY_RELAY_INDICES = [3, 4]
RELAY_EVENTS = [
    "4x50fr",
    "4x100fr",
    "4x200fr",
    "4x50mr",
    "4x100mr",
    ]

INDIVIDUAL_TO_RELAY_INDICES = {
    "50fr" : [0, 3],
    "100fr" : [1, 4],
    "200fr" : [2],
    "50ba" : [3],
    "100ba" : [4],
    "50br" : [3],
    "100br" : [4],
    "50fl" : [3],
    "100fl" : [4]
}
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
        pdfReader = PyPDF2.PdfReader(pdfFileObj)
        pageObj = pdfReader.pages[0]
        text = pageObj.extract_text()
    return text

def generate_indices(length):
    '''
    Returns an array of all 0's with length ``length``.
    '''
    return [0] * length

def new_2d_array(length):
    '''
    Returns an empty 2-d array with length ``length``.
    '''
    permutation = []
    for _ in range(length):
        permutation.append([])
    return permutation

def generate_event_combinations(swimmer_events : dict[str, list[int]],
                                relays_per_swimmer : int, 
                                swimmer_event_limits
                                ) -> tuple[bool, dict[str, list[list[int]]]]:
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
    
    swimmer_exceeded_limit = False
    swimmer_combinations = {}
    # find swimmers who exceeded relay limit
    for swimmer, events in swimmer_events.items():
        limit = swimmer_event_limits[swimmer] if swimmer in swimmer_event_limits.keys() else relays_per_swimmer
        if len(events) > limit:
            combinations = [list(tup) for tup in itt.combinations(events, limit)]
            swimmer_combinations[swimmer] = combinations
            swimmer_exceeded_limit = True
        elif len(events) == limit:
            pass
            #swimmer_combinations[swimmer] = [events]

    return swimmer_exceeded_limit, swimmer_combinations

def remove_swimmers_from_rankings(rankings: list[list[tuple[str,str]]], 
                                  excluded_swimmers):
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

def medley_relay_helper(rankings: list[list[tuple[str,str]]], 
                         team: list[tuple[str,str]],
                         excluded_swimmers: list[str]
                         ) -> list[list[tuple[str,str]]]:
    '''
    Returns a list of possible medley relay teams that are selected greedily.
    '''
    new_team = team.copy()
    # indices of relays each swimmer is apart of
    name_count = defaultdict(list)

    possible_teams = []

    for i, pair in enumerate(team):
        stroke_rankings = rankings[i]
        idx = 0
        while idx < len(stroke_rankings) and stroke_rankings[idx][0] in excluded_swimmers:
            idx += 1
        if idx == len(stroke_rankings):
            return [new_team]
        
        if pair is None:
            if len(stroke_rankings) == 0:
                return []
            new_team[i] = stroke_rankings[idx]
        name = new_team[i][0]
        name_count[name].append(i)

    # TODO: run recursive method after entire for loop is done
    for name in name_count.keys():
        indices = name_count[name]
        if len(indices) > 1:
            # swimmer is first for multiple legs of the relay
            temp_rankings = remove_swimmers_from_rankings(rankings, [name])
            combinations = list(itt.combinations(indices, len(indices)-1))
            for combination in combinations:
                temp_team = new_team.copy()
                for index in combination:
                    temp_team[index] = None
                possible_teams += medley_relay_helper(temp_rankings, temp_team, excluded_swimmers)

    if len(possible_teams) == 0:
        possible_teams.append(new_team)

    return possible_teams

def medley_relay_team(rankings: list[list[tuple[str,str]]],
                      excluded_swimmers: list[str],):
    possible_teams = medley_relay_helper(rankings, [None, None, None, None], excluded_swimmers)

    best_time = 0
    best_team = None
    for team in possible_teams:
        if None in team:
            continue
        total_time = 0
        for pair in team:
            time = convert_time_to_seconds(pair[1])
            total_time += time
        if best_team is None or total_time < best_time:
            best_team = team
            best_time = total_time
    
    return best_team

def free_relay_team(
        rankings: list[tuple[str,str]], 
        team: list[tuple[str,str]],
        excluded_swimmers : list[str]
    ) -> list[tuple[str, str]]:
    '''
    Returns the best free relay team for an event.

    Parameters
    ----------
    rankings : arr of tuples
        An ordered array of tuples, each tuple containing the full name of the swimmer
        along with their time. See extract_rankings for more details.

    Returns
    -------
    teams : array of tuples
        An array representing one relay team and contains 4 tuples in the format
          of (full name, time) representing the swimmers in the relay.
    '''

    names = []
    for pair in team:
        if pair is None:
            continue
        names.append(pair[0])
            
    curr_team = team.copy()
    idx = 0
    for i, pair in enumerate(team):
        if pair is not None:
            continue
        while (idx < len(rankings) and (rankings[idx][0] in names or rankings[idx][0] in excluded_swimmers)):
            idx += 1
        if idx == len(rankings):
            break
        curr_team[i] = rankings[idx]
        names.append(rankings[idx][0])
        idx += 1
    return curr_team

def get_swimmer_combinations(
        event_combinations: dict[str, list[list[int]]]) -> list[list[list[int]]]:
    '''
    Returns a list of combinations 'c'. 'c' is a 2-d array where each array c[i]
    is an array of indices of the relays that the swimmer at 
    event_combinations.keys()[i] can swim.
    '''
    all_combinations = []
    names = list(event_combinations.keys())

    def helper(idx, combination: list[list[int]]):
        if idx == len(names):
            all_combinations.append(combination)
            return
        name = names[idx]
        combinations = event_combinations[name]
        for c in combinations:
            helper(idx + 1, combination + [c])

    helper(0, [])

    return all_combinations

def generate_lineup(
        all_rankings: dict[str, list[tuple[str,str]]], 
        names: list[str],
        combination: list[list[int]],
        relay_teams: dict[str, list[tuple[str,str]]],
        swimmer_event_limits: dict[str, int],
        previous_assigned_events: dict[str, list[int]],
        relays_per_swimmer: int
                            ) -> tuple[
                                dict[str, list[int]], 
                                dict[str, list[tuple[str,str]]]
                                ]:
    '''
    Returns a lineup for all relays.

    Parameters
    ----------
    all_rankings : dict
        key : event name
        value : array of tuples with rankings
        A dictionary of rankings for each event. See extract_rankings for more details.
    
    Returns
    -------
    swimmer_events : dict
        key : swimmer name
        value : array of indices of the relays the swimmer is apart of
        A dictionary describing which relays a swimmer will swim. For each index i in the array,
        the swimmer will be swimming the ith relay in ``EVENTS``.

    relay_groups : dict
        key : event
        value : array with a length of ``relays_per_event``.
        A dictionary describing the relay team for each event. 
        See ``relay_teams`` for more details.       
    '''

    swimmer_events = defaultdict(list)
    curr_relay_teams = defaultdict(list)
    
    # copy combination
    for i, name in enumerate(names):
        swimmer_events[name] = combination[i].copy()

    # copy relay groups and removing swimmers from events that aren't in their combination
    event_idx = 0
    for event, team in relay_teams.items():
        tc = team.copy()
        for i, pair in enumerate(team):
            if pair is None:
                continue
            name = pair[0]
            if event_idx not in swimmer_events[name]:
                tc[i] = None
        curr_relay_teams[event] = tc
        event_idx += 1

    limited_swimmers_with_mr = {}

    # reset medley relays with <4 people in it
    for mr_idx in MEDLEY_RELAY_INDICES:
        event = RELAY_EVENTS[mr_idx]
        team = curr_relay_teams[event]
        if None not in team:
            # team is filled with swimmers
            continue
        for i, pair in enumerate(team):
            if pair is None:
                continue
            name = pair[0]
            limit = swimmer_event_limits[name] if name in swimmer_event_limits.keys() else relays_per_swimmer
            if len(swimmer_events[name]) == limit:
                #condition is necessary to only add events once, otherwise 
                #if a swimmer is in two medley relays it will overwrite the previous full lineup
                limited_swimmers_with_mr[name] = swimmer_events[name].copy()
            swimmer_events[name].remove(mr_idx)
            team[i] = None
    maxed_swimmers = []

    for name, events in swimmer_events.items():
        limit = swimmer_event_limits[name] if name in swimmer_event_limits.keys() else relays_per_swimmer
        if len(events) == limit:
            maxed_swimmers.append(name)
    
    all_rankings = remove_swimmers_from_all_rankings(all_rankings, maxed_swimmers)

    for event_index, relay_name in enumerate(RELAY_EVENTS):
        # if relay team is already filled, skip
        if None not in curr_relay_teams[relay_name]:
            continue
        
        excluded_swimmers = []
        for name, events in limited_swimmers_with_mr.items():
            if event_index not in events:
                excluded_swimmers.append(name)
        
        for name, events in previous_assigned_events.items():
            if event_index in events:
                excluded_swimmers.append(name)

        team = curr_relay_teams[relay_name]
        if relay_name in FREE_RELAYS.keys():
            #free relays
            individual_event_name = FREE_RELAYS[relay_name]
            rankings = all_rankings[individual_event_name]

            relay_team = free_relay_team(rankings, team, excluded_swimmers)

            if None in relay_team:
                # not enough swimmers to fill freestyle relay
                return None, None
            
            curr_relay_teams[relay_name] = relay_team

            for pair in relay_team:
                name = pair[0]
                if event_index not in swimmer_events[name]:
                    swimmer_events[name].append(event_index)
        else:
            #medley relays
            medley_rankings = []

            #TODO: make this cleaner with list/dict
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
            
            relay_team = medley_relay_team(medley_rankings, excluded_swimmers)

            if relay_team is None:
                return None, None

            curr_relay_teams[relay_name] = relay_team
            for pair in relay_team:
                name = pair[0]
                if event_index not in swimmer_events[name]:
                    swimmer_events[name].append(event_index)

    return swimmer_events, curr_relay_teams


def generate_all_lineups(
        prev_event_combinations: dict[str, list[list[int]]], 
        prev_relay_teams: dict[str, list[tuple[str,str]]],
        rankings: dict[str, list[tuple[str,str]]],
        relays_per_swimmer: int, 
        top_events, 
        swimmer_event_limits: dict[str, int], 
        all_event_combinations: list[dict[str, list[list[int]]]],
        previous_assigned_events: dict[str, list[int]]
        ) -> tuple[
            list[tuple[dict[str, list[int]], dict[str, list[tuple[str,str]]]]],
            list[dict[str, list[list[int]]]]
        ]:
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

    current_combinations = get_swimmer_combinations(prev_event_combinations)
    
    lineups = []

    names = list(prev_event_combinations.keys())

    if len(names) == 0:
        current_combinations.append([])

    for curr_combination in current_combinations:
        swimmer_events, relay_teams = generate_lineup(
            rankings, names, curr_combination, 
            prev_relay_teams, swimmer_event_limits, previous_assigned_events,
            relays_per_swimmer)

        if swimmer_events is None:
            # not enough swimmers for one of the relays, skip this combination
            continue

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

        swimmer_exceeded_limit, event_combinations = generate_event_combinations(
            swimmer_events, relays_per_swimmer, swimmer_event_limits)

        if swimmer_exceeded_limit:
            # At least one swimmer is signed up to swim more than ``relays_per_swimmer`` relays.\

            # for swimmers who have events locked in, add them back in 
            for i, name in enumerate(names):
                events = curr_combination[i]
                if name not in event_combinations.keys():
                    event_combinations[name] = [events]

            # checks if current combination has been tried before
            if event_combinations in all_event_combinations:
                continue

            all_event_combinations.append(event_combinations)

            generated_lineups = generate_all_lineups(
                event_combinations, relay_teams, rankings, relays_per_swimmer, 
                top_events, swimmer_event_limits, all_event_combinations,
                previous_assigned_events)

            lineups += generated_lineups
        else:
            lineups.append((swimmer_events, relay_teams))
    
    return lineups

def write_rankings(rankings):
    with open('rankings.txt','w') as f:
        for event, list in rankings.items():
            f.write(event+'\n')
            f.write(str(list)+'\n')

def get_fastest_lineup(lineups, gender):
    best = None
    best_points = 0

    #find best lineup
    for lineup in lineups:
        total_points = 0
        relay_teams = lineup[1]
        for event, relay_team in relay_teams.items():
            total_time = 0
            #hard-coded for one relay team per event
            if len(relay_team) == 0:
                continue
            for pair in relay_team:
                time = convert_time_to_seconds(pair[1])
                total_time += time
            if total_time == 0:
                continue
            total_points += calculate_points(event, total_time, gender)
        total_points /= len(RELAY_EVENTS)

        if best is None or total_points > best_points:
            best = lineup
            best_points = total_points

    return best, best_points

def swimmer_minimum_events(all_rankings: dict[str, list[tuple[str,str]]],
                           relays_per_swimmer: int, 
                           previous_assigned_events):
    '''
    Finds the minimum number of events that certain swimmers should swim.
    '''
    top_swimmers = {}

    mr_50 = ["50fr", "50ba", "50br", "50fl"]
    mr_100 = ["100fr","100ba","100br","100fl"]

    for i, event in enumerate(RELAY_EVENTS):
        if event[-2:] == "mr":
            individual_events = mr_50 if event == "4x50mr" else mr_100
            for individual_event in individual_events:
                rankings = all_rankings[individual_event]
                for pair in rankings:
                    name = pair[0]
                    if name in previous_assigned_events and i in previous_assigned_events[name]:
                        # swimmer already swimming this event
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
                if name in previous_assigned_events and i in previous_assigned_events[name]:
                    # swimmer already swimming this event
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
        if name in previous_assigned_events.keys():
            event_lineup = previous_assigned_events[name]
            limit -=  len(event_lineup)
        top_swimmers[name] = min(events, limit)

    return top_swimmers

def extract_all_rankings(school_name, gender) -> dict[str, list[tuple[str,str]]]:
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

def generate_best_lineup(teams_per_event, relays_per_swimmer, school_name, gender):
    global temp
    all_rankings = extract_all_rankings(school_name, gender)

    complete_lineup = {
        "Maximum Relays Per Event": teams_per_event,
        "Maximum Relays Per Swimmer": relays_per_swimmer,
    }

    modified_rankings = all_rankings.copy()
    swimmer_event_limits = {}

    total_event_indices = defaultdict(list)
    previous_assigned_events = {}

    for i in range(teams_per_event):
        temp = i
        # all_event_combinations.clear()
        t0 = perf_counter()
        team_name = TEAM_NAMES[i]
        print(f"Finding best lineup for {team_name}...")

        minimum_events = swimmer_minimum_events(modified_rankings, relays_per_swimmer, previous_assigned_events)

        relay_teams = {}
        for event in RELAY_EVENTS:
            relay_teams[event] = [None] * 4

        lineups = generate_all_lineups(defaultdict(list), relay_teams, modified_rankings, 
                                          relays_per_swimmer, minimum_events, 
                                          swimmer_event_limits, [], previous_assigned_events)
        
        lineup, points = get_fastest_lineup(lineups, gender)

        if lineup is None:
            print(f"Not enough swimmers for {team_name}.")
            break

        swimmer_events = lineup[0]
        relay_teams = lineup[1]
        complete_lineup[team_name] = {
            "Average Points Per Relay": points,
            "Lineup": relay_teams,
        }

        # reset rankings based on previous relay teams
        maxed_swimmers = []
        swimmer_event_limits.clear()
        previous_assigned_events.clear()

        for swimmer, event_lineup in swimmer_events.items():
            prev_events = total_event_indices[swimmer]

            if len(prev_events) + len(event_lineup) == relays_per_swimmer:
                # maxed out relays
                maxed_swimmers.append(swimmer)
            else:
                swimmer_event_limits[swimmer] = relays_per_swimmer - (len(event_lineup) + len(prev_events))
                previous_assigned_events[swimmer] = event_lineup
            total_event_indices[swimmer] = prev_events + event_lineup

        modified_rankings = remove_swimmers_from_all_rankings(modified_rankings, maxed_swimmers)

        print(f"Finished in {round(perf_counter() - t0,2)} seconds.")

    with open(f'lineup_{teams_per_event}_rpe_{relays_per_swimmer}_rps_{gender}.json','w') as f:
        json.dump(complete_lineup,f,indent = 2)

    print(f"Finished.")
    
def check_swimmer_limit(relays_per_event, relays_per_swimmer, gender):
    data = {}
    with open(f'lineup_{relays_per_event}_rpe_{relays_per_swimmer}_rps_{gender}.json','r') as f:
        data = json.load(f)
    swimmer_count = defaultdict(int)
    for team in TEAM_NAMES.values():
        if team not in data.keys():
            continue
        lineup_data = data[team]
        lineup = lineup_data["Lineup"]
        for relay_team in lineup.values():
            for pair in relay_team:
                name = pair[0]
                swimmer_count[name] += 1
                if swimmer_count[name] <= relays_per_swimmer:
                    continue
                print(f"{name} set to swim more than {relays_per_swimmer} events.")
                return
    print(f"All swimmers within {relays_per_swimmer} events.")

def main():
    school_name = "California Institute of Technology"
    gender = "female"
    teams_per_event = 3
    relays_per_swimmer = 3
    generate_best_lineup(teams_per_event, relays_per_swimmer, school_name, gender)
    check_swimmer_limit(teams_per_event, relays_per_swimmer, gender)

if __name__=="__main__":
    main()