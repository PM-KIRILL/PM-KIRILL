import time
import os
import requests
import re
from utils import extractor
import config

class Chatlink():
    def __init__(self):
        self.death_messages_regex = self.compile_regex()
        self.advancements_regex = {
            r"^[a-zA-Z0-9_]+ has made the advancement \[.+\]$": config.advancement_message,
            r"^[a-zA-Z0-9_]+ has reached the goal \[.+\]$": config.goal_message,
            r"^[a-zA-Z0-9_]+ has completed the challenge \[.+\]$": config.challenge_message
        }
        self.stop = False
        
    #compile regex patterns
    def compile_regex(self):
        print("Fetching a list of death messages...")
        extractor_obj = extractor.Extractor(config.version)
        death_messages = extractor_obj.get_death_messages()
        death_messages_regex = []
        placeholder1 = re.escape("%1$s")
        placeholder2 = re.escape("%2$s")
        placeholder3 = re.escape("%3$s")
        for death_msg in death_messages:
            death_message_escaped = re.escape(death_msg)
            death_message_escaped = death_message_escaped.replace(placeholder1, "[a-zA-Z0-9_]+")
            death_message_escaped = death_message_escaped.replace(placeholder2, ".+").replace(placeholder3, ".+")
            death_messages_regex.append(re.compile("^"+death_message_escaped+"$"))
        return death_messages_regex

    #detects changes in the log file and returns them
    def tail(self, filename, logdir):
        f = open(filename, "r")
        while not f.readline() == "":
            pass

        all_files = os.listdir(logdir)
        while self.stop == False:
            all_files_old = all_files[:]
            all_files = os.listdir(logdir)
            if len(all_files) > len(all_files_old):
                #reopen the log file if the server restarts
                print("server start detected")
                f.close()
                f = open(filename, "r")
                
            newline = f.readline()
            if newline == "":
                try:
                    time.sleep(0.5)
                except KeyboardInterrupt:
                    print("quitting...")
                    break
            else:
                yield newline
        f.close()

    def main(self):
        for line in self.tail(config.log_file, os.path.dirname(config.log_file)):
            if line == "!stop_chatlink":
                break
            line_stripped = re.sub(r"(\[[0-9][0-9]:[0-9][0-9]:[0-9][0-9]])", "", line, count=1).lstrip()
            if not "[Server thread/INFO]:" in line_stripped:
                continue
            line_formatted = line_stripped.replace("[Server thread/INFO]: ", "").replace("\n", "")
            if line_formatted == "":
                continue
            line_split = line_formatted.split(" ")

            #check for player message
            if re.match(r"^<[a-zA-Z0-9_]+> .+$", line_formatted):
                if line_formatted.startswith("<--[HERE]"):
                    continue
                player = re.findall(r"<(.*?)>", line_formatted)[0]
                chatmsg = line_formatted.replace("<{player}> ".format(player=player), "", 1)
                yield config.player_message.format(player=player, chatmsg=chatmsg); continue
            #check for message sent by /say
            elif re.match(r"^\[[a-zA-Z0-9_]+\] .+$", line_formatted):
                findall = re.findall(r"\[(.*?)\]", line_formatted)
                if not len(findall) > 0:
                    continue
                player = findall[0]
                if player in config.blacklisted_users:
                    continue
                elif " " in player:
                    continue
                chatmsg = line_formatted.replace("[{player}] ".format(player=player), "", 1)
                yield config.slash_say_message.format(player=player, chatmsg=chatmsg); continue

            #check for player join/leave
            if re.match(r"^[a-zA-Z0-9_]+ left the game$", line_formatted):
                    player = line_split[0]
                    yield config.player_leave_message.format(player=player); continue
            elif re.match(r"^[a-zA-Z0-9_]+ joined the game$", line_formatted):
                    player = line_split[0]
                    yield config.player_join_message.format(player=player); continue

            #check for server start/stop
            if re.match(r'^Done \(.+\)! For help, type "help"$', line_formatted):
                yield config.server_start_message; continue
            elif line_formatted == "Stopping server":
                yield config.server_stop_message; continue

            #check for advancements
            for regex in self.advancements_regex:
                if re.match(regex, line_formatted):
                    message = self.advancements_regex[regex]
                    line_split_re = re.split(r"\[(.*?)\]", line_formatted)
                    player_string = line_split_re[0]
                    player_string_split = player_string.split(" ", 1)
                    advancement = line_split_re[1]
                    yield message.format(player=player_string_split[0], advancement=advancement); continue
                    
            #check for death messages
            for regex in self.death_messages_regex:
                if not regex.search(line_formatted) == None:
                    yield config.death_message.format(deathmsg=line_formatted); break

if __name__ == "__main__":
    if config.webhook == True:
        chatlink_object = Chatlink()
        for line in chatlink_object.main():
            print("MC -> Discord: "+text)
            data = {
                "content": text,
                "username": config.discord_nickname
            }
            r = requests.post(config.webhook_url, json=data)
            
