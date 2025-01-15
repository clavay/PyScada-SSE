// Connect to broadcast event
var broadcast_events = new ReconnectingEventSource('/events/broadcast/');

broadcast_events.addEventListener('message', function (e) {
    console.log(e.data);
}, false);

broadcast_events.addEventListener('stream-reset', function (e) {
    console.log("stream-reset");
    console.log(e.data);
}, false);

broadcast_events.addEventListener('stream-error', function (e) {
    console.log("stream-error");
    console.log(e.data);
}, false);

// Connect to session events
var session_events = new ReconnectingEventSource('/events/session/{{ request.session.session_key }}/');

session_events.addEventListener('message', function (e) {
    console.log(e.data);
}, false);

session_events.addEventListener('stream-reset', function (e) {
    console.log("stream-reset");
    console.log(e.data);
}, false);

session_events.addEventListener('stream-error', function (e) {
    console.log("stream-error");
    console.log(e.data);
}, false);


/**
* Query historical data using date time range and chart variables keys list
* @returns void
*/
function query_historical_data() {
    data = JSON.stringify({
        start: ((DATA_DISPLAY_FROM_TIMESTAMP == -1) ? DATA_FROM_TIMESTAMP : DATA_DISPLAY_FROM_TIMESTAMP),
        end: ((DATA_DISPLAY_TO_TIMESTAMP == -1) ? DATA_TO_TIMESTAMP : DATA_DISPLAY_TO_TIMESTAMP),
        variable_ids: CHART_VARIABLE_KEYS.keys(),
        view_link_title: document.querySelector("body").dataset["viewTitle"],
    });
    console.log(data);
    fetch("/need_historical_data/", {
    method: "POST",
    body: data,
    headers: {
        "Content-type": "application/json; charset=UTF-8",
        'X-CSRFToken': CSRFTOKEN,
    }
    })
    .then((response) => response.json())
    .then((json) => console.log(json));
};

// query historic on date time range change


console.log("PyScada SSE : loaded.");
