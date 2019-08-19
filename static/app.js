/**
* Initiate global websocket object.
*/
var host = location.origin.replace(/^http/, 'ws')
var ws = new WebSocket(host +"/socket/" + location.pathname.replace('/room/', '').replace('/', ''));

//Get cookie by name
function cookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

$(document).ready(function() {
    if (!window.console) window.console = {};
    if (!window.console.log) window.console.log = function() {};

    $("#chat-input").submit(function() {
        postMessage($(this));
        return false;
    });
    $("#message-input").focus();
    $('html, body').animate({scrollTop: $(document).height()}, 800);

    var disabled = $("form#chat-input").find("input");
    disabled.attr("disabled", "disabled");

    ws.onopen = function() {
        console.log("Connected...");
        disabled.removeAttr("disabled");
    };

    ws.onmessage = function(event) {
        data = JSON.parse(event.data);
        if(data.textStatus && data.textStatus == "unauthorized") {
            alert("unauthorized");
            disabled.attr("disabled", "disabled");
        }
        else if(data.error && data.textStatus) {
            alert(data.textStatus);
        }
        console.log("New Message", data);
        if (data.messages) newMessages(data);
    };

    ws.onclose = function() {
        console.log("Closed!");
        disabled.attr("disabled", "disabled");
    };
});

function postMessage(form) {
    var value = form.find("input[type=text]").val();
    var message = {body: value};
    message._xsrf = cookie("_xsrf");
    message.user = cookie("user");
    var disabled = form.find("input");
    disabled.attr("disabled", "disabled");
    ws.send(JSON.stringify(message));
    console.log("Created message (successfuly)");
    $("#message-input").val("").select();
    disabled.removeAttr("disabled");
}

updater = {}
newMessages = function (data) {
    var messages = data.messages;
    if(messages.length == 0) return;
    updater.cursor = messages[messages.length - 1]._id;
    console.log(messages.length + "new messages, cursor: " + updater.cursor);
    for (var i = 0; i < messages.length; i++) {
        showMessage(messages[i]);
    }
};

showMessage = function(message) {
    console.log("Show Message");
    var existing = $("#m" + message._id);
    if (existing.length > 0) return;
    $("#messsages").append('<div style="display: none;" class="message" id="' + message._id + '"><b>' + message.from + ': </b>' + message.body + '</div>');
    $('#messsages').find(".message:last").slideDown("fast", function(){
        $('html, body').animate({scrollTop: $(document).height()}, 400);
    });
};
