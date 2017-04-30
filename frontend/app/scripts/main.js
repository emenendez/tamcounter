var settings = {
    'oauth_uri': 'https://www.strava.com/oauth/authorize?client_id=6518&redirect_uri=http://tamcounter.com/&response_type=code&scope=view_private',
    'api_uri': 'https://api.tamcounter.com/get_activity_counts',
}

// Thank you https://www.joezimjs.com/javascript/3-ways-to-parse-a-query-string-in-a-url/
var parseQueryString = function( queryString ) {
    var params = {}, queries, temp, i, l;
    // Split into key/value pairs
    queries = queryString.substring(1).split('&');
    // Convert the array of strings into an object
    for ( i = 0, l = queries.length; i < l; i++ ) {
        temp = queries[i].split('=');
        params[temp[0]] = temp[1];
    }
    return params;
};

var updateUrl = function(athlete_id) {
    window.history.replaceState(null, null, 'athlete/' + athlete_id);
};

(function () {
    var params = parseQueryString(window.location.search);

    if (params.code || params.athlete) {
        // request api with params
        d3.json(settings.api_uri).post(JSON.stringify(params), function(error, response) {
            for (var category in response.activities) {
                var categoryElement = d3.select('#' + category);
                // Set activity count
                categoryElement.select('.count').text(response.activities[category].length);
                // Add activity dots
                categoryElement.select('.activities')
                    .selectAll('a')
                    .data(response.activities[category])
                    .enter().append('a')
                        .attr('class', 'circle')
                        .attr('href', function(d) {
                            return 'https://www.strava.com/activities/' + d; });
            }
            updateUrl(response.athlete_id);
        });
        if (params.athlete) {
            updateUrl(params.athlete);
        }

    }
    else {
        // redirect to strava oauth
        window.location = settings.oauth_uri;
    }

}());
