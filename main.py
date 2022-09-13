from lib2to3.pytree import convert
from re import L
import PyPDF2, pprint, json, math
import itertools as itt

printer = pprint.PrettyPrinter()

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

def calculate_points(event, swim_time):
    '''
    Returns the power points calculated by Swimcloud's performance rankings:
    https://support.swimcloud.com/hc/en-us/articles/360052519314-How-are-performance-rankings-calculated-
    '''
    base_time = RELAY_RECORDS_MEN[event]
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
        An ordered array of tuples, each with a length of 2. The formatting of the tuples are
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
    with open(file_name, "rb") as pdfFileObj:
        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
        pageObj = pdfReader.getPage(0)
        return pageObj.extractText()

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

def generate_swimmer_combinations(swimmer_events, relays_per_swimmer):
    '''
    Returns all possible combinations for the relays that each swimmer can swim if they 
    exceed ``relays_per_swimmer``.

    Parameters
    ----------
    swimmer_events : dict
        key : swimmer name
        value : array of indices of the relays the swimmer is apart of
        A dictionary describing which relays a swimmer will swim. For each index i in the array,
        the swimmer will be swimming the ith relay in ``EVENTS``.
    
    relays_per_swimmer : int
        The maximum number of relays each swimmer can swim.

    Returns
    -------
    swimmer_combinations : dict
        key : swimmer name
        value : 2-d array of ints
            Each sub-array contains the indices of the relays that a swimmer can take part in and
            is restricted to a length of ``relays_per_swimmer``. Each sub-array represents a possible
            lineup for the relays that the swimmer can take part in.
    '''
    swimmer_combinations = {}
    # find swimmers who exceeded relay limit
    for swimmer, events in swimmer_events.items():
        if len(events) > relays_per_swimmer:
            combinations = list(itt.combinations(events, relays_per_swimmer))
            swimmer_combinations[swimmer] = combinations
    return swimmer_combinations

def remove_swimmer_from_mr_rankings(rankings, excluded_swimmers):
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
    printer = pprint.PrettyPrinter()
    new_team = team.copy()
    name_count = {}

    possible_teams = []

    for i, pair in enumerate(team):
        if pair is None:
            if len(rankings[i]) == 0:
                return []
            new_team[i] = rankings[i][0]
        name = new_team[i][0]
        if name not in name_count.keys():
            name_count[name] = [i]
        else:
            name_count[name].append(i)
    
    for name in name_count.keys():
        indices = name_count[name]
        if len(indices) > 1:
            # swimmer is first for multiple legs of the relay
            temp_rankings = remove_swimmer_from_mr_rankings(rankings, excluded_swimmers + [name])
            combinations = list(itt.combinations(indices, len(indices)-1))
            for combination in combinations:
                temp_team = team.copy()
                for index in combination:
                    temp_team[index] = None
                possible_teams += medley_relay_repeats(temp_rankings, temp_team, excluded_swimmers)
    
    if len(possible_teams) == 0:
        possible_teams.append(new_team)

    return possible_teams

def medley_relay_teams(rankings, excluded_swimmers, relays_per_event):
    '''
    rankings : 2-d array, length 4
    '''
    modified_rankings = remove_swimmer_from_mr_rankings(rankings, excluded_swimmers)
    teams = []

    # generate ``relays_per_event`` medley relay teams
    for i in range(relays_per_event):
        printer = pprint.PrettyPrinter()
        team = []
        name_count = {}

        possible_teams = []
        out_of_swimmers = False
        for i, stroke_rankings in enumerate(modified_rankings):
            if len(stroke_rankings) == 0:
                out_of_swimmers = True
                break
            pair = stroke_rankings[0]
            team.append(pair)
            name = pair[0]
            if name not in name_count.keys():
                name_count[name] = [i]
            else:
                name_count[name].append(i)

        if out_of_swimmers:
            break
        # team contains the fastest swimmer for each stroke, regardless of repeats

        for name in name_count.keys():
            indices = name_count[name]
            if len(indices) > 1:
                # swimmer is first for multiple legs of the relay
                temp_rankings = remove_swimmer_from_mr_rankings(modified_rankings, excluded_swimmers + [name])
                combinations = list(itt.combinations(indices, len(indices)-1))
                for combination in combinations:
                    temp_team = team.copy()
                    for index in combination:
                        temp_team[index] = None
                    possible_teams += medley_relay_repeats(temp_rankings, temp_team, excluded_swimmers)

        if len(possible_teams) == 0:
            teams.append(team)
        else:
            best_time = 0
            best_team = None
            for team in possible_teams:
                total_time = 0
                for pair in team:
                    time = convert_time_to_seconds(pair[1])
                    total_time += time
                if best_team is None or total_time < best_time:
                    best_team = team
                    best_time = total_time
            teams.append(best_team)
        

        to_exclude = []
        for pair in teams[-1]:
            name = pair[0]
            to_exclude.append(name)
        
        modified_rankings = remove_swimmer_from_mr_rankings(modified_rankings, to_exclude)
    
    return teams

def free_relay_teams(rankings, excluded_swimmers, relays_per_event):
    '''
    Returns the best relay team(s) for an event.

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

    for i in range(relays_per_event):
        team = []
        if len(modified_rankings) >= (i+1) * 4:
            start_index = i * 4
            for j in range(4):
                team.append(modified_rankings[start_index + j])
        teams.append(team)

    return teams

def generate_lineup(all_rankings, excluded_swimmers_2d, relays_per_event = 3):
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

    relays_per_event : int
        The number of relay teams to generate lineups for. If ``relays_per_event`` is 
        set to None, then it is set to 3 by default.
    
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
            relay_group = free_relay_teams(rankings, excluded_swimmers_2d[event_index], relays_per_event)
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
            
            relay_group = medley_relay_teams(medley_rankings, excluded_swimmers_2d[event_index], relays_per_event)

            relay_groups[relay_name] = relay_group
            for relay_team in relay_group:
                for pair in relay_team:
                    name = pair[0]
                    if name not in swimmer_events.keys():
                        swimmer_events[name] = [event_index]
                    else:
                        swimmer_events[name].append(event_index)
    return swimmer_events, relay_groups

def generate_all_lineups(swimmer_combinations, rankings, relays_per_swimmer, relays_per_event):
    '''
    Returns a list of all possible lineups.

    Parameters
    ----------
    swimmer_combinations : dict
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

    swimmer_combination_arrays = []

    # convert swimmer_combinations to string form
    for swimmer, combinations in swimmer_combinations.items():
        combination_arrays = []
        for combination in combinations:
            combination_array = [""] * len(EVENTS)
            for i in range(len(EVENTS)):
                if i not in combination:
                    combination_array[i] = swimmer
            combination_arrays.append(combination_array)
        swimmer_combination_arrays.append(combination_arrays)

    #printer.pprint(swimmer_combination_arrays)

    indices = generate_indices(len(swimmer_combination_arrays))

    exceeded_permutations = []

    # generate permutations
    while len(swimmer_combination_arrays) > 0 and indices[-1] < len(swimmer_combination_arrays[-1]):
        start_index = indices[0]
        first_combination = swimmer_combination_arrays[0][start_index]

        # initialize permutation
        forbidden_swimmers = []
        for c in first_combination:
            exceeded = []
            if c != '':
                exceeded.append(c)
            forbidden_swimmers.append(exceeded)
        
        # add other names to permutation
        for i in range(1,len(swimmer_combination_arrays)):
            index = indices[i]
            combination = swimmer_combination_arrays[i][index]
            for j,c in enumerate(combination):
                if c != '':
                    forbidden_swimmers[j].append(c)
        
        exceeded_permutations.append(forbidden_swimmers)
        
        # update indices
        indices[0] += 1
        for i in range(len(indices)-1):
            if indices[i] == len(swimmer_combination_arrays[i]):
                indices[i] = 0
                indices[i+1] += 1
    
    
    lineups = []
    if len(exceeded_permutations) == 0:
        exceeded_permutations.append(new_2d_array(len(EVENTS)))

    for i, forbidden_swimmers in enumerate(exceeded_permutations):
        swimmer_events, relay_groups = generate_lineup(rankings, forbidden_swimmers, relays_per_event)
        this_swimmer_combinations = generate_swimmer_combinations(swimmer_events, relays_per_swimmer)
        # recursively call this function with the new restriction
        if len(this_swimmer_combinations.keys()) > 0:
            for swimmer, combinations in swimmer_combinations.items():
                this_swimmer_combinations[swimmer] = combinations
            generated_lineups = generate_all_lineups(this_swimmer_combinations, rankings, relays_per_swimmer, relays_per_event)
            for lineup in generated_lineups:
                if lineup not in lineups:
                    lineups.append(lineup)
        else:
            if (swimmer_events, relay_groups) not in lineups:
                if len(swimmer_events["Leo Yang"]) == 2:
                    print(swimmer_events["Leo Yang"])
                    printer.pprint(rankings)
                with open("test","a") as f:
                    f.write(str(swimmer_events)+'\n')
                lineups.append((swimmer_events, relay_groups))
    
    return lineups
    
def main():
    printer = pprint.PrettyPrinter()

    # extract rankings
    rankings = {}
    for event in INDIVIDUAL_EVENTS:
        rankings[event] = extract_rankings(f"California Institute of Technology - Top Times - {event}.pdf", "California Institute of Technology")

    relays_per_event = 1
    relays_per_swimmer = 3

    lineups = generate_all_lineups({}, rankings, relays_per_swimmer, relays_per_event)

    best_lineup = None
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
            total_points += calculate_points(event, total_time)
        total_points /= len(EVENTS)
        if best_lineup == None or total_points > best_points:
            best_lineup = lineup
            best_points = total_points

    with open('lineups.json','w') as f:
        json.dump([best_lineup,total_points],f,indent = 2)
    print("Done.")


if __name__=="__main__":
    main()
