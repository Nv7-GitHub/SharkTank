from flask import Flask, render_template, redirect, request, session
import os
import json
from random import randint
import datetime
from datetime import timedelta
from multiprocessing import Process, Manager
manager = Manager()


def save_games():
    with open('games.json', mode='w') as savegames:
        json.dump(games, savegames)


def save_accounts():
    with open('accounts.json', mode='w') as saveaccounts:
        json.dump(accounts, saveaccounts)


if not ((len(open("games.json").read()) == 0) or (len(open("accounts.json").read()) == 0)):
    loadgames, loadaccounts = open("games.json"), open("accounts.json")
    games = json.load(loadgames)
    accounts = json.load(loadaccounts)
    loadgames.close()
    loadaccounts.close()

else:
    accounts = []
    games = []
    save_games()
    save_accounts()

hosted = manager.list([])
unhosted = manager.list([])
unhostedgames = manager.list()


def codeexists(code):
    for game in hosted:
        if str(game["code"]) == str(code):
            return True

    return False


def exists(username):
    for account in accounts:
        if account["username"] == username:
            return True


def valid(username, password):
    for account in accounts:
        if account["username"] == username and account["password"] == password:
            return True

    return False


def get_user(username):
    for user in accounts:
        if user["username"] == username:
            return user


def updategames():
    while True:
        # print("Running")
        for key, game in enumerate(hosted):
            if str(datetime.datetime.now().replace(second=0, microsecond=0)) == str(game["end"]):
                unhosted.append(key)
                unhostedgames.append(hosted[key])
                del hosted[key]


app = Flask(__name__)
app.secret_key = os.urandom(100)


@app.route('/', methods=["GET"])
def init():
    session["username"] = ""
    session["signedin"] = False
    return redirect('/home')


@app.route('/home', methods=["GET"])
def home():
    return render_template("home.html", signedin=session.get('signedin'), username=session.get('username'),
                           message=request.args.get("message", ""))


@app.route('/gotonewaccount', methods=["POST", "GET"])
def gotonewaccount():
    return render_template("newaccount.html", message=request.args.get('message', ''))


@app.route('/newaccount', methods=["POST"])
def newaccount():
    if not exists(request.form["username"]):
        accounts.append(
            {
                "username": request.form["username"],
                "password": request.form["password"],
                "games": []
            }
        )
        save_accounts()
        session["username"] = request.form["username"]
        session["signedin"] = True
        return redirect('/home')

    else:
        return redirect('/gotonewaccount?message=Username Already Exists')


@app.route('/join', methods=["POST"])
def join():
    for key, game in enumerate(hosted):
        if str(game["code"]) == str(request.form["code"]):
            hosted[key]["players"].append(
                {
                    "name": request.form["name"],
                    "upgrades": [1, 1, int(hosted[key]["money"])],  # $/question, multiplier, money
                    "points": int(hosted[key]["upgrade"])
                }
            )

            return redirect(f'/play?user={len(hosted[key]["players"]) - 1}&game={key}')

    return redirect("/home?message=Game Doesn't Exist")


@app.route('/gotologin', methods=["POST", "GET"])
def gotologin():
    return render_template('login.html', message=request.args.get('message', ''))


@app.route('/login', methods=["POST"])
def login():
    if valid(request.form["username"], request.form["password"]):
        session["signedin"] = True
        session["username"] = request.form["username"]
        return redirect('/home')

    else:
        return redirect('/gotologin?message=A Detail Was Incorrect')


@app.route('/games', methods=["POST", "GET"])
def gotogames():
    return render_template("games.html", signedin=session["signedin"], user=get_user(session["username"]),
                           games=games)


@app.route('/newgame', methods=["POST"])
def newgame():
    games.append(
        {
            "name": "New Game",
            "questions": [
               {
                    "question": "How do you edit this question?",
                    "answers": ['Press "Return To Home"', 'Press "Edit Question"', 'Press "I want FOOD"', 'Say Hi'],
                    "correct": "choice2"
                }
            ],
            "id": len(games)
        }
    )
    save_games()
    for user in accounts:
        if user["username"] == session["username"]:
            user["games"].append(len(games) - 1)
    save_accounts()

    return redirect('/games')


@app.route('/delete', methods=["POST"])
def deletegame():
    del games[int(request.form["gameid"])]

    i = int(request.form["gameid"])
    while i < len(games):
        games[i]["id"] -= 1
        i += 1

    save_games()

    location = "Unknown"
    for key, account in enumerate(accounts):
        if str(account) == str(request.form["user"]):
            location = key

    for key, game in enumerate(accounts[location]["games"]):
        if game == int(request.form["gameid"]):
            del accounts[location]["games"][key]

    for key, account in enumerate(accounts):
        for location, game in enumerate(account["games"]):
            if game > int(request.form["gameid"]):
                accounts[key]["games"][location] -= 1

    save_accounts()

    return redirect('/games')


@app.route('/logout', methods=["POST"])
def logout():
    session["signedin"] = False
    session["username"] = ""
    return redirect('/home')


@app.route('/open', methods=["POST"])
def opengame():
    return redirect(f'/editgame?game={games[int(request.form["gameid"])]}')


@app.route('/editgame', methods=["GET"])
def editgame():
    return render_template("game.html", game=eval(request.args.get("game")))


@app.route('/newquestion', methods=["POST"])
def gotonewquestion():
    return render_template("newquestion.html", gameid=request.form["game"])


@app.route('/runnewquestion', methods=["POST"])
def newquestion():
    games[int(request.form["gameid"])]["questions"].append(
        {
            "question": request.form["question"],
            "answers": [request.form["choice1"], request.form["choice2"], request.form["choice3"],
                        request.form["choice4"]],
            "correct": request.form["correct"]
        }
    )
    save_games()

    return redirect(f'/editgame?game={games[int(request.form["gameid"])]}')


@app.route('/deletequestion', methods=["POST"])
def deletequestion():
    del games[int(request.form["game"])]["questions"][int(request.form["id"]) - 1]

    save_games()

    return redirect(f'/editgame?game={games[int(request.form["game"])]}')


@app.route('/editquestion', methods=["POST"])
def gotoeditquestion():
    question = games[int(request.form["game"])]["questions"][int(request.form["id"]) - 1]
    answers = question["answers"]
    return render_template("editquestion.html", question=question["question"], choice1=answers[0],
                           choice2=answers[1], choice3=answers[2], choice4=answers[3],
                           id=int(request.form["id"]) - 1, correct=question["correct"], gameid=request.form["game"])


@app.route('/runeditquestion', methods=["POST"])
def editquestion():
    games[int(request.form["gameid"])]["questions"][int(request.form["id"])] = {
        "question": request.form["question"],
        "answers": [request.form["choice1"], request.form["choice2"], request.form["choice3"],
                    request.form["choice4"]],
        "correct": request.form["correct"]
    }

    save_games()

    return redirect(f'/editgame?game={games[int(request.form["gameid"])]}')


@app.route('/rename', methods=["POST"])
def rename():
    games[int(request.form["gameid"])]["name"] = request.form["name"]

    save_games()

    return redirect("/games")


@app.route('/gotohost', methods=["POST"])
def gotohost():
    return redirect(f'/host?game={request.form["gameid"]}')


@app.route('/host', methods=["GET"])
def gotohostgame():
    return render_template("hostgame.html", gameid=request.args.get("game"))


@app.route('/runhost', methods=["POST"])
def hostgame():
    code = "Quiz Royale"
    found = False
    while not found:
        found = True
        code = randint(0, 100 + len(hosted))
        if codeexists(code):
            found = False

    hosted.append(
        {
            "game": int(request.form["id"]),
            "players": [],
            "code": code,
            "mode": request.form["mode"],
            "increment": request.form["increment"],
            "money": request.form["money"],
            "upgrade": request.form["upgrade"],
            "end": datetime.datetime.now().replace(second=0, microsecond=0) + timedelta(
                minutes=int(request.form["time"]))
        }
    )

    return redirect(f'/playgame?game={len(hosted) - 1}')


@app.route('/playgame', methods=["GET"])
def playgame():
    if not int(request.args.get('game')) in unhosted:
        game = hosted[int((request.args.get("game", "")))]
        return render_template("codedisplay.html", game=game, timer=str(game["end"] - datetime.datetime.now().
                                                                        replace(microsecond=0)))

    elif int(request.args.get('game')) in unhosted:
        location = "Unknown"
        for key, number in enumerate(unhosted):
            if number == int(request.args.get('game')):
                location = key

        one = ""
        two = ""
        three = ""
        for player in unhostedgames[location]["players"]:
            if not one == "":
                if player["upgrades"][2] > one["upgrades"][2]:
                    placeholder = two
                    two = one
                    three = placeholder
                    one = player

            else:
                one = player

        del unhosted[location]
        return render_template("gameover.html", one=one, two=two, three=three)

    else:
        return redirect('/home')


@app.route('/play', methods=["POST", "GET"])
def play():
    if not int(request.args.get("game")) in unhosted:
        game = hosted[int(request.args.get("game"))]
        game["end"] = game["end"]
        gamekey = int(request.args.get("game"))
        user = int(request.args.get("user"))
        questionnumber = randint(0, len(games[int(game["game"])]["questions"]) - 1)
        question = games[int(game["game"])]["questions"][questionnumber]["answers"]
        questionquestion = games[int(game["game"])]["questions"][questionnumber]["question"]
        return render_template("question.html", choice1=question[0], choice2=question[1],
                               choice3=question[2], choice4=question[3], game=game, user=user,
                               question=questionnumber, questionquestion=questionquestion,
                               url=f'/play?game={gamekey}&user={user}', useruser=game["players"][user],
                               gamekey=gamekey)

    else:
        return redirect('/home')


@app.route('/answer', methods=["POST"])
def answer():
    game = eval(request.form["game"])
    game["players"] = []
    question = games[int(game["game"])]["questions"][int(request.form["questionnumber"])]
    hostedindex = "Unknown"
    answercheck = games[int(game["game"])]["questions"][int(request.form["questionnumber"])]
    answer = answercheck["answers"][int(answercheck["correct"][int(len(answercheck["correct"]) - 1)]) - 1]
    for key, hostedgame in enumerate(hosted):
        hostedgamecheck = hostedgame.copy()
        hostedgamecheck["players"] = []
        if hostedgamecheck == game:
            hostedindex = key
            player = hosted[hostedindex]["players"][int(request.form["user"])]

    if not hostedindex == "Unknown":
        if request.form["choice"] == question["correct"]:
            player["upgrades"][2] += player["upgrades"][0] * player["upgrades"][1]
            return render_template("answer.html", hostedindex=hostedindex, user=request.form["user"], correct=True,
                                   answer=answer, hosted=hosted, games=games, url=request.form["url"],
                                   useruser=hosted[hostedindex]["players"][int(request.form["user"])],
                                   game=request.form["gamekey"])

        else:
            player["upgrades"][2] -= player["upgrades"][0] * player["upgrades"][1]
            return render_template("answer.html", hostedindex=hostedindex, user=request.form["user"], correct=False,
                                   answer=answer, hosted=hosted, games=games, url=request.form["url"],
                                   useruser=hosted[hostedindex]["players"][int(request.form["user"])],
                                   game=request.form["gamekey"])

    else:
        return redirect('/')


@app.route('/upgrade', methods=["GET", "POST"])
def upgrade():
    url = f'/play?user={request.args.get("user")}&hostedindex={request.args.get("hostedindex")}&' \
        f'game={request.args.get("game")}'
    user = int(request.args.get('user'))
    hostedindex = int(request.args.get('hostedindex'))
    player = hosted[hostedindex]["players"][user]
    return render_template('upgrades.html', user=user, hostedindex=hostedindex, url=url, player=player)


@app.route('/upgradevalue', methods=["POST"])
def upgradevalue():
    hosted[int(request.form["hostedindex"])]["players"][int(request.form["user"])][
        "upgrades"][2] -= hosted[int(request.form["hostedindex"])]["players"][int(request.form["user"])]["upgrades"
                          ][int(request.form["item"])] ** 2
    hosted[int(request.form["hostedindex"])]["players"][int(request.form["user"])]["upgrades"][
        int(request.form["item"])] += 1

    return redirect(f'/upgrade?url={request.form["url"]}&user={request.form["user"]}&'
                    f'hostedindex={request.form["hostedindex"]}')


if __name__ == "__main__":
    updategames = Process(target=updategames)
    updategames.daemon = True
    updategames.start()
    app.run(host="0.0.0.0", port="8080")
