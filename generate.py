from nltk import CFG
from nltk import ChartParser # parse_cfg, ChartParser
from random import choice
import re
from enum import Enum, auto

class Name:
    class NameOrder(Enum):
        Eastern = auto()
        Forename_Only = auto()
        Surname_Only = auto()
        Western = auto()
        
    class NameBank(Enum):
        American = auto()
        Dwarf = auto()
        French = auto()
        Gaelic = auto()
        Germanic = auto()
        Orc = auto()
        Portuguese = auto()
        
    class NameType(Enum):
        Forename = auto()
        Surname = auto()
        
    class Origin(Enum):
        Aquatic = auto()
        Desert = auto()
        Mountain = auto()
        Tundra = auto()
        Urban = auto()
        Forest = auto()
        Air = auto()
        
    def __init__(self):
        self.gender_male = False
        self.gender_female = False
        self.gender_neutral = False
        
        self.has_position = False
        self.order = Name.NameOrder.Western

class FileFetcher():
    def __init__(self):
        pass
    
    def get_gender_endings(self, config, always_neutral=False):
        e = []
        if config.gender_male:
            e.append("male")
        if config.gender_female:
            e.append("female")
        if config.gender_neutral or always_neutral:
            e.append("")
        if len(e) == 0:
            print("No Gender Selection. Defaulting to gender neutral")
            e.append("")
        return e
    
    def get_position_files(self, config):
        ges = self.get_gender_endings(config)
        pt = []
        for g in ges:
            g = f"-{g}" if g != "" else g
            pt.append(f'prefixes/positions{g}.txt')
         
        return pt

class Grammar:
    def __init__(self, config):
        self.config = config
        self.obj = {}
        self.root = "S"
        self.ff = FileFetcher()
        
    def initialize(self):
        self.obj[self.root]= ["PRE", "CORE", "POST"]
        
        self.basic_tokens()

    def basic_tokens(self):
        self.obj["SPC"] = ["' '"]
        self.obj["OF"] = ["'o'", "'f'"]

    def define_position(self, config, optional=False):
        
        # Prefix
        positions = self.ff.get_position_files(config)
        positions = [f"['{p}']" for p in positions]
        self.obj["PRE"] = ["TITLE", "SPC"]
        if optional:
            self.obj["PRE"].append(None)
        
        self.obj["TITLE"] = positions
       
        # Postfix
        origin = config.origin.name.lower()
               
        self.obj["POST"] = ["SPC", "OF", "SPC", "WHERE"]
        if optional:
            self.obj["POST"].append(None)
        # TODO: Allow multiple origins
        self.obj["WHERE"] = [f"['postfixes/{origin}.txt']",]
     
    def setNameOrder(self, order):
        if order == Name.NameOrder.Western:
            self.obj["CORE"] = ["FORENAME", "SPC", "SURNAME"]
        elif order == Name.NameOrder.Eastern:
            self.obj["CORE"] = ["SURNAME", "SPC", "FORENAME"]
        elif order == Name.NameOrder.Forename_Only:
            self.obj["CORE"] = ["FORENAME"]
        elif order == Name.NameOrder.Surname_Only:
            self.obj["CORE"] = ["FORENAME"]
        else:
            print("Unimplemented Name Order: ", config.order, ". Defaulting to Western")
            self.setNameOrder(Name.NameOrder.Western)


    def getNamesFromBank(self, config, name_type):
        ges = self.ff.get_gender_endings(config)
        namebank = config.namebank.name.lower()
        name_type = name_type.name.upper()
        
        pt = []
        for g in ges:
            g = f"-{g}" if g != "" else g
            # TODO: s shouldnt be there.
            pt.append(f'{name_type.lower()}s/{namebank}{g}.txt')
        self.obj[name_type] = [pt]
        
    def constructName(self, config, name_type):
        origin = config.origin.name.lower()
        name_type = name_type.name.upper()
                   
        self.obj[name_type] = ["ADJ", "NOUN"]
        
        self.buildAdjBank(config)
        self.buildNounBank(config)
        
    def buildAdjBank(self, config):
        origin = config.origin.name.lower()
        
        pt = []
        # TODO: Dodginess/Alignment. John Bloodsword seems more evil than John Goldheart
        pt.append(f"['adjectives/{origin}.txt']")
         
        self.obj["ADJ"] = pt
        
    def buildNounBank(self, config):
        origin = config.origin.name.lower()
        
        pt = []
        # TODO: Dodginess/Alignment. John Poisonblood seems more evil than John Goldheart
        pt.append(f"['nouns/{origin}.txt']")
        self.obj["NOUN"] = pt
        
        

    def write(self, filename="custom.grammar"):
        # TODO: order carefully
        s = ""
        for key, value in self.obj.items():
            s += f"{key} -> "
            for i, v in enumerate(value):
                sep = " "
                if v is None:
                    v = " | "
                s += f"{v}{sep}"
            s += "\n"
                
        #print("Grammar")
        #print(s)
        self.string_repr = s
        f = open(filename, "w")
        f.write(s)
        f.close()
        return filename

    def __str__(self):
        if hasattr(self, "string_repr"):
            return self.string_repr
        else:
            return "Not Finalized"

def define_grammar(config):

    grammar = Grammar(config)
    grammar.initialize()
    if config.has_position:
        grammar.define_position(config)
    grammar.setNameOrder(config.order)
    grammar.getNamesFromBank(config, Name.NameType.Forename)
    grammar.constructName(config, Name.NameType.Surname)
    
    return grammar.write()

def resolve_grammar(G):
    def file_contents(s):
        filename = f"name-segments/{s.group(1)}"
        try:
            terms = open(filename).readlines()
            s = ""
            for i, t in enumerate(terms):
                t = t.replace("\n","")
				# Allow Commenting
                if "#" not in t:
                    seperator = "|" if i > 0 else ""
                    s += f"{seperator} '{t}' "       
        except FileNotFoundError:
            print("Warn: File doesn't exist:", filename)
            s = ""
        return s

    G = re.sub("\[\'([a-zA-Z\-\.\/]*)\'\]", file_contents, G)
    return G

def generate_name(G):
    grammar = CFG.fromstring(G)    

    parser = ChartParser(grammar)

    gr = parser.grammar()
    tokens = produce(gr, gr.start())
    name = ''.join(tokens)
    return name.title()

def produce(grammar, symbol):
    words = []
    productions = grammar.productions(lhs = symbol)
    production = choice(productions)
    for sym in production.rhs():
        if isinstance(sym, str):
            words.append(sym)
        else:
            words.extend(produce(grammar, sym))
    return words


config = Name()
config.has_position = True
config.origin = Name.Origin.Mountain
config.namebank = Name.NameBank.Dwarf
config.order = Name.NameOrder.Western
config.gender_male = True
grammar_file = define_grammar(config)

G = resolve_grammar(open(grammar_file).read())
name = generate_name(G)

print("Your Character:", name)

#print(G)
