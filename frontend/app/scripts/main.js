var settings = {
    'oauth_uri': 'https://www.strava.com/oauth/authorize?client_id=6518&redirect_uri=http://tamcounter.com/&response_type=code&scope=view_private',
    'api_uri': 'https://vyq2vscpyc.execute-api.us-west-2.amazonaws.com/dev/get_activity_counts',
}

// Thank you https://www.joezimjs.com/javascript/3-ways-to-parse-a-query-string-in-a-url/
var parseQueryString = function( queryString ) {
    var params = {}, queries, temp, i, l;
    // Split into key/value pairs
    queries = queryString.split("&amp;");
    // Convert the array of strings into an object
    for ( i = 0, l = queries.length; i < l; i++ ) {
        temp = queries[i].split('=');
        params[temp[0]] = temp[1];
    }
    return params;
};

(function () {
    params = parseQueryString(Window.location.search);

    if (params.code || params.athlete) {
        // request api with params
        d3.json(settings.api_uri).post(params, function(error, response) {
            console.log(response);
        });

    }
    else {
        // redirect to strava oauth
        Window.location = settings.oauth_uri;
    }
// d3.select('body')

}());




