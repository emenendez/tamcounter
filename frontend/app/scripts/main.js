var settings = {
    'scheme': 'http://',
    'domain': 'tamcounter.com',
};
settings.oauth_uri = 'https://www.strava.com/oauth/authorize?client_id=6518&redirect_uri=' +
                     settings.scheme + settings.domain + '/&response_type=code&scope=view_private';
settings.api_uri = 'https://api.tamcounter.com/get_activity_counts';

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

var updateUrl = function(athlete_id, add_social_buttons) {
    var path = '/athlete/' + athlete_id;
    var uri = settings.scheme + settings.domain + path;

    window.history.replaceState(null, null, path);

    d3.select('link[rel=canonical]').attr('href', uri);
    d3.select('meta[property="og:url"]').attr('content', uri);

    if (add_social_buttons) {
        d3.select('.twitter').append('a')
            .attr('class', 'twitter-share-button')
            .attr('href', 'https://twitter.com/intent/tweet?text=See%20my%20#Tamcount:')
            .attr('data-size', 'large');
        if (window.twttr && window.twttr.widgets) {
            window.twttr.widgets.load();
        }

        d3.select('.facebook').append('div')
            .attr('class', 'fb-share-button')
            .attr('data-href', uri)
            .attr('data-layout', 'button_count')
            .attr('data-size', 'large');
        if (window.FB && window.FB.XFBML) {
            window.FB.XFBML.parse();
        }
    }
};

(function () {
    Raven.config('https://86428fc26eb146c3ba69848d1ca01d46@sentry.io/164686').install()

    var params = parseQueryString(window.location.search);

    if (params.code || params.athlete) {
        // request api with params
        d3.json(settings.api_uri).post(JSON.stringify(params), function(error, response) {
            if (error) {
                d3.selectAll('.callouts > div').classed('hidden', true);
                d3.select('#error').classed('hidden', false);
            } else {
                for (var category in response.activities) {
                    var categoryElement = d3.select('#' + category);
                    // Set activity count
                    categoryElement.select('.count').text(response.activities[category].length);
                    // Add activity dots
                    categoryElement.select('.activities')
                        .selectAll('a')
                        .data(response.activities[category].filter(function(element) {
                            return !element.private;
                        }))
                        .enter().append('a')
                            .attr('class', 'tower')
                            .attr('href', function(d) {
                                return 'https://www.strava.com/activities/' + d.id;
                            })
                            .attr('title', function(d) {
                                return d.start_date_local ? ( d.start_date_local + ( d.name ? ': ' + d.name : '' ) ) : '';
                            });
                }
                updateUrl(response.athlete_id, true);
            }
        });
        if (params.athlete) {
            updateUrl(params.athlete, false);
        }
    }
    else {
        // redirect to strava oauth
        window.location = settings.oauth_uri;
    }

}());
