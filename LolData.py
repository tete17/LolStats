#!/usr/bin/env python3

# import calendar
import time
from functional import seq
import json
import requests
import xlsxwriter

ranked5v5Queue = 440


class LolApplication:
    def __init__(self, apikey):
        self.baseUrl = "https://euw1.api.riotgames.com"
        self.headers = {"X-Riot-Token": apikey}

    def getAccountId(self, summonerName):
        r = requests.get(
            self.baseUrl + "/lol/summoner/v3/summoners/by-name/" + summonerName.strip(),
            headers=self.headers,
        )

        assert r.status_code == 200

        return r.json()["accountId"]

    def getRankedGameIds(self, accountId):
        matchListRequest = requests.get(
            self.baseUrl + "/lol/match/v3/matchlists/by-account/" + str(accountId),
            params={"endIndex": 100},
            headers=self.headers,
        )

        return seq(matchListRequest.json()["matches"]) \
            .filter(lambda match: match["queue"] == ranked5v5Queue) \
            .map(lambda match: match["gameId"])

    def getStatsPerPlayer(self, gameId, accountId):
        matchInfoRequest = requests.get(
            self.baseUrl + "/lol/match/v3/matches/" + str(gameId),
            headers=self.headers,
        )

        print(matchInfoRequest.status_code)

        matchInfo = matchInfoRequest.json()

        participantId = \
            seq(matchInfo["participantIdentities"]) \
                .filter(lambda participant: participant["player"]["accountId"] == accountId) \
                .map(lambda participant: participant["participantId"]) \
                .head()

        teamId = \
            seq(matchInfo["participants"]) \
                .filter(lambda participant: participant["participantId"] == participantId) \
                .map(lambda participant: participant["teamId"]) \
                .head()

        participantIdToSummonerName = \
            seq(matchInfo["participantIdentities"]) \
                .map(lambda participant: [participant["participantId"], participant["player"]["summonerName"]]) \
                .dict()

        return seq(matchInfo["participants"]) \
            .filter(lambda participant: participant["teamId"] == teamId) \
            .map(lambda participant: participant["stats"]) \
            .map(lambda stats: [participantIdToSummonerName[stats["participantId"]],
                                {**stats,
                                 "gameDuration": matchInfo["gameDuration"]}]) \
            .dict()


def getChampionName(championId):
    with open("champion.json") as f:
        data = json.load(f)["data"]

    return seq(data.values()) \
        .filter(lambda champion: champion["key"] == str(championId)) \
        .map(lambda champion: champion["name"]) \
        .head()


if __name__ == "__main__":
    app = LolApplication("")

    accountId = app.getAccountId("Gcw Eicca")

    print(accountId)

    gameIds = app.getRankedGameIds(accountId)

    allStats = {}

    for gameId in gameIds:
        time.sleep(1.5)
        stats = app.getStatsPerPlayer(gameId, accountId)

        for playerName, stat in stats.items():
            if playerName in allStats:
                allStats[playerName].append(stat)
            else:
                allStats[playerName] = [stat]

    workbook = xlsxwriter.Workbook("Data.xlsx")

    for playerName, stats in allStats.items():
        worksheet = workbook.add_worksheet(playerName)

        for x, column in seq(stats[0].keys()).zip_with_index():
            worksheet.write(0, column, x)

        for data, row in seq(stats).zip_with_index(1):
            for x, column in seq(data.values()).zip_with_index():
                worksheet.write(row, column, x)

    workbook.close()

    print(allStats)

