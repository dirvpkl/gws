from datetime import time


class GWProviders:
    Unknown = 0
    BlessMeBot = 1
    CryptoBot = 2
    Callback = 3
    GiveShareBot = 4
    TGGrowBot = 5
    BestContestsBot = 6
    ConcuBot = 7
    TicketsBot = 8
    BestRandomBot = 9
    GiwayTechBot = 10
    FortuneSmileMeBot = 11
    GiveawayLuckyBot = 12
    RandomBeastBot = 13
    SubInviteBot = 14
    GiveawayRandomBot = 15
    RozygryshiGiveBot = 16
    RandomGiveBot_Bot = 17
    ContestyBot = 18
    ContestMasterV3 = 19
    MegaMarket = 101
    BigLuckBot = 103
    Aurora = 104
    Fonbet = 105
    VTB = 106
    RandomCapBot = 233


GWProvidersKeywords = {
    "random1zebot": GWProviders.BlessMeBot,
    "randomgodbot": GWProviders.BlessMeBot,
    "randomized": GWProviders.BlessMeBot,
    "random": GWProviders.BlessMeBot,
    "blessmebot": GWProviders.BlessMeBot,
    "cryptobot": GWProviders.CryptoBot,
    "callback": GWProviders.Callback,
    "givesharebot": GWProviders.GiveShareBot,
    "giveawaybot": GWProviders.GiveShareBot,
    "tggrowbot": GWProviders.TGGrowBot,
    "best_contests_bot": GWProviders.BestContestsBot,
    "concubot": GWProviders.ConcuBot,
    "ticketsbot": GWProviders.TicketsBot,
    "bestrandom_bot": GWProviders.BestRandomBot,
    "giway_tech_bot": GWProviders.GiwayTechBot,
    "fortunesmilemebot": GWProviders.FortuneSmileMeBot,
    "giveawayluckybot": GWProviders.GiveawayLuckyBot,
    "randombeast_bot": GWProviders.RandomBeastBot,
    "subinvitebot": GWProviders.SubInviteBot,
    "giveaway_random_bot": GWProviders.GiveawayRandomBot,
    "rozygryshi_give_bot": GWProviders.RozygryshiGiveBot,
    "randomgivebot_bot": GWProviders.RandomGiveBot_Bot,
    "contestybot": GWProviders.ContestyBot,
    "contentmasterv3bot": GWProviders.ContestMasterV3,
    "mmgift_bot": GWProviders.MegaMarket,
    "big_luck_bot": GWProviders.BigLuckBot,
    "auroragivebot": GWProviders.Aurora,
    "fonbetprize_bot": GWProviders.Fonbet,
    "vtb_priz_bot": GWProviders.VTB,
    "randomcapbot": GWProviders.RandomCapBot,
}

GWProvidersPostTags = {
    GWProviders.Unknown: "unknown ❓",
    GWProviders.BlessMeBot: "BlessMeBot 🎲",
    GWProviders.CryptoBot: "CryptoBot 💲",
    GWProviders.Callback: "Callback ♻️",
    GWProviders.GiveShareBot: "GiveShareBot 🔍",
    GWProviders.TGGrowBot: "TggrowBot 🎩",
    GWProviders.BestContestsBot: "bestcontestsbot 🙈",
    GWProviders.ConcuBot: "Concubot 🥇",
    GWProviders.TicketsBot: "Ticketsbot 🙈",
    GWProviders.BestRandomBot: "Bestrandombot 🙈",
    GWProviders.GiwayTechBot: "Ramblerbot 🙈",
    GWProviders.FortuneSmileMeBot: "FortuneSmileMeBot 🙈",
    GWProviders.GiveawayLuckyBot: "GiveawayLuckyBot 🙈",
    GWProviders.RandomBeastBot: "RandomBeastBot 🙈",
    GWProviders.SubInviteBot: "SubAndInviteBot 🙈",
    GWProviders.GiveawayRandomBot: "Giveaway_Random_bot 🙈",
    GWProviders.RozygryshiGiveBot: "Rozygrishi_Give_bot 🙈",
    GWProviders.RandomGiveBot_Bot: "RandomGivebot_bot 🙈",
    GWProviders.ContestyBot: "Contestybot 🙈",
    GWProviders.ContestMasterV3: "ContestMasterV3 🙈",
    GWProviders.MegaMarket: "MegaMarket 🛒",
    GWProviders.BigLuckBot: "Bigluckbot 🟣",
    GWProviders.Aurora: "Aurora 🙈",
    GWProviders.Fonbet: "Fonbet 🙈",
    GWProviders.VTB: "VTB 🙈",
    GWProviders.RandomCapBot: "Randomcapbot 🙈",
}


class Ports:
    AI_SERVER = "ai_server"
    DEEPGLOW = "deepglow"


class RediskaPrefixes:
    TIME = "time"


class Tasks:
    Task = "task"

    Participate = "participate"
    Subscribe = "subscribe"
