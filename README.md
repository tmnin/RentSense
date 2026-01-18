# RentSense

RentSense is a multi-criteria decision analysis tool that helps you find where you should live - not just where you can. 

Our team built a data pipeline that aggregates multiple open public datasets, like NYPD crime reports and rent data, into a single, consistent geographic unit: New York City Neighbourhood Tabulation Areas (NTAs). We rate every individual NTA on criteria like safety, amenity access, and commute time, and assign each NTA an overall "fit index" calculated with a summation algorithm. 

The exact weight of each criterion is completely adjustable. Users who may have a difficult time quantifying their preferences can utilize our implementation of Google Gemini's API. The agent will ask specific, detailed questions, and adjust the weights of each category accordingly. If they prefer, users may also directly adjust the weights themselves using interactive sliders. 

Our tool is the first on the market to offer relocation recommendations that are tailored to individual preferences. Outside of calculating a fit index, our tool also calculates "return upon investment" - in other words, how much fit does this location offer you, considering average rent costs? 

You choose: best fit or best value.

Built for NexHacks @ CMU, 2026