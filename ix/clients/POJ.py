import lxml.html
from base64 import b64encode
from . import login_required, request, with_cookie, Env

USER = "user_id1"
PASS = "password1"

CREDENTIAL_INPUT_TITLE = "POJ (poj.org)"
CREDENTIAL_INPUT_FIELDS = (
    (USER, "User ID", False),
    (PASS, "Password", True),
)

ENVS = {
    Env(name="MinGW",      ver="4.4.0", os="Windows", arch="x86", lang="C++",     lang_ver="C++03")       : "0",
    Env(name="MinGW",      ver="4.4.0", os="Windows", arch="x86", lang="C",       lang_ver="C99")         : "1",
    Env(name="JDK",        ver="6",     os="Windows", arch="x86", lang="Java",    lang_ver="Java 6")      : "2",
    Env(name="FreePascal", ver="2.2.0", os="Windows", arch="x86", lang="Pascal",  lang_ver="Free Pascal") : "3",
    Env(name="MSVC",       ver="2008",  os="Windows", arch="x86", lang="C++",     lang_ver="C++03")       : "4",
    Env(name="MSVC",       ver="2008",  os="Windows", arch="x86", lang="C",       lang_ver="C99")         : "5",
    Env(name="MinGW",      ver="4.4.0", os="Windows", arch="x86", lang="Fortran", lang_ver="Fortran 95")  : "6",
}

request_with_credential = with_cookie("cookie")(request)

def is_post_success(status, headers):
    return status == 302 and headers.get("location") == "http://poj.org/status"


def login(client):
    if "cookie" not in client.credential:
        status, headers, body = client.get(
            "http://poj.org/",
            request = request_with_credential)
        if status != 200:
            return None

    status, headers, body = client.post_form(
        "http://poj.org/login",
        { USER: client.credential[USER],
          PASS: client.credential[PASS],
          "B1": "login",
          "url": "/status"},
        request=request_with_credential)

    if not is_post_success(status, headers):
        return None

    status, headers, body = client.get(
        "http://poj.org/submit",
        request=request_with_credential)

    if status != 200:
        return None
    if body.startswith(b"<form method=POST action=login>"):
        return False

    return True


def fetch(client, problem):
    status, _, body = client.get("http://poj.org/problem", {"id":problem})
    if status != 200:
        return False
    doc = lxml.html.fromstring(body.decode("utf-8"))
    input, output = doc.xpath('//pre[@class="sio"]/text()')
    return [{"in": input, "out": output}]


@login_required
def submit(client, problem, env, code):
    status,headers,body = client.post_form(
        "http://poj.org/submit",
        { "source": b64encode(code.encode("utf-8")),
          "problem_id": problem,
          "language": env,
          "submit": "Submit",
          "encoded": "1"},
        request=request_with_credential)

    if not is_post_success(status, headers):
        if b'Please login first.' in body:
            return None
        return False

    return {"user_id": client.credential[USER], "language": env}


def check(client, problem, token):
    status, headers, body = client.get(
        "http://poj.org/status",
        { "problem_id": problem,
          "user_id": token["user_id"],
          "result": "",
          "language": token["language"]})

    if status != 200:
        return False

    doc = lxml.html.fromstring(body.decode("utf-8"))
    run_id = token.get("run_id", None)
    if run_id is None:
        tr = doc.xpath('//table[@class="a"]/tr[@align="center"][1]')
        if not tr:
            return False
        tr = tr[0]

        run_id, = tr.xpath('td[1]/text()')
        token["run_id"] = run_id
    else:
        tr = doc.xpath('//table[@class="a"]/tr[@align="center"][td[1]/text()="' + run_id + '"]')
        if not tr:
            return False
        tr = tr[0]

    result, = tr.xpath('td[4]//font[1]/text()')
    color, = tr.xpath('td[4]//font[1]/@color')

    if color == 'blue':
        mem, = tr.xpath('td[5]/text()')
        time, = tr.xpath('td[6]/text()')
        return (True, result, True, 'Memory: %s, Time: %s'%(mem ,time))
    else:
        return (not(color == 'green' and result != 'Compile Error'), result, False)
