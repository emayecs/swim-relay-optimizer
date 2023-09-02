# Swim Relay Optimizer

## Overview
This script generates the best relay lineup for a swim team given the following two restrictions:
* restrictions on the number of relay teams per event
    * e.g. if this restriction is set to 2, then there can only be an 'A' and 'B' team for each relay event.
* the number of relays each swimmer can be apart of
    * e.g. if this restriction is set to 3, then each swimmer can only be used on 3 different relay teams at most.

## Calculations
The best lineup is decided based on the total number of points that the entire lineup scores.

Points are calculated using Swimcloud's methodology [here](https://support.swimcloud.com/hc/en-us/articles/360052519314-How-are-performance-rankings-calculated), where base times are the NCAA D1 records as of March 2022.

## Data
Times are pulled from Swimcloud (e.g. [Caltech's page](https://www.swimcloud.com/team/187/times/)), saved as PDFs, renamed, and scraped. The best lineup is then written to a json file.

## Future Improvements
* Automating web scraping
* Adding mixed relay functionality
* Considering relay start times
