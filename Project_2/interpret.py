#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 24.3.2019

@author: Radek Duchoň
"""
import getopt
import re
import sys
import xml.etree.ElementTree as ET

#Funkce pro nacteni argumentu
def argParse(argv):
    args = dict()
    args['--source'] = ''
    args['--input'] = ''
    args['--stats'] = ''
    try:
        argList, options = getopt.getopt(argv[1:], '', ['help', 'source=', 'input=', 'stats=', 'insts', 'vars'])
        for arg in argList:
            args[arg[0]] = arg[1]
    except:
        pass

    if '--help' in args and len(argv[1:]) is not 1:
        print("--help musi byt osamote")
        sys.exit(10)
    if ('--insts' in args or '--vars' in args) and args['--stats'] is '':
        print("Nepolovena kombinace")
        sys.exit(10)
    if args['--source'] is '' and args['--input'] is '' and '--help' not in args:
        print("Chybejici argument")
        sys.exit(10)
    
    if '--help' in args:
        print("Napoveda: Program je nutno spustit s parametry --source=file nebo --input=file se vstupnimi soubory.")
        print(" V případě chybějícího jednoho parametru bude brán standardní vstup.")
        print(" Program take pracuje s argumentem --stats=file, ktery vyzaduje alespon jeden z argumentu --insts nebo --vars.")
        print(" --insts a --vars naopak vyzaduji zadany argument --stats=file, spolecne slouzi pro zaznamenavani statistik.")
        sys.exit(0)

    return args

#Funkce ziskavajici xml ze zadaneho vstupu
def xmlGet(filename):
    fp = sys.stdin
    if filename != '':
        try:
            fp = open(filename, 'r')
        except:
            print("nelze otevrit soubor")
            sys.exit(11)
    #Postupne hledani hlavicky (v pripade, ze neni na prvnim radku vstupu)
    xml = fp.readline()
    while xml.strip() == '':
        xml = fp.readline()
        if xml == "":
            print("prazdny soubor")
            sys.exit(0)
    xml = xml.strip()
    #Detailni kontrola hlavicky
    if xml[0:14] != '<?xml version=' or xml[15:18] != '1.0' or xml[19:29] != ' encoding=' or xml[30:35] != 'UTF-8' or xml[36:] != '?>' or xml[14] != xml[18] or xml[29] != xml[35]:
        print("Chybna hlavicka")
        sys.exit(32)

    for line in fp:
        xml += line

    try:
        return ET.fromstring(xml)
    except:
        print("Chybne xml")
        sys.exit(31)

#Pomocna funkce pro nahrazeni escape sekvenci
def replace(match):
        return chr(int(match.group(1)))

#Funkce pro zpracovani xml
def xmlParse(filename):
    xml = xmlGet(filename)
    regex = re.compile(r"\\(\d{3})")
    if xml.tag != 'program' or 'language' not in xml.attrib or xml.attrib['language'] != 'IPPcode19':
        print("chybna hlavicka")
        sys.exit(32)
    instructions = list()
    for inst in xml:
        if inst.tag != 'instruction':
            print('instrukce se nejmenuje instruction')
            sys.exit(32)
        instructions.append('')
        for i in range(len(inst)):
            if inst[i].text == None:
                inst[i].text = ''
            elif re.fullmatch('(([^\s\\\\#])|(\\\\\d{3}))*', inst[i].text, re.DOTALL):
                inst[i].text = regex.sub(replace, str(inst[i].text))
            else:
                print("Nepovolene znaky")
                sys.exit(32)
            #Prohazovani spatne argumentu serazenych instrukci
            for j in range(i):
                if inst[i].tag < inst[j].tag:
                    inst[i], inst[j] = inst[j], inst[i]
    
    length = len(instructions)
    #Kontrola hodnoty order a serazeni instrukci
    for inst in xml:
        order = 0
        try:
            order = int(inst.attrib['order'])
        except:
            print("order instrukce neni cislo")
            sys.exit(32)

        if length < order or order <= 0 or instructions[order - 1] != '':
            print("Chybny order instrukce")
            sys.exit(32)
        
        instructions[order - 1] = inst

    return instructions

#Pomocna funkce pro kontrolu hodnoty promenne dle typu
def symbCheck(symb, symbType):
    regex = '.*'
    if symbType == 'int':
        regex = '[-+]?\d+'
    elif symbType == 'bool':
        regex = 'false|true'
    elif symbType == 'nil':
        regex = 'nil'
    elif symbType == 'label':
        regex = '[_a-zA-Z-$&%*?!][_a-zA-Z-$&%*?!\d]*'
    elif symbType == 'var':
        regex = '(L|G|T)F@[_a-zA-Z-$&%*?!][_a-zA-Z-$&%*?!\d]*'
    elif symbType == 'float':
        regex = '[+-]?0x[01]\.[\da-fA-F]*p[+-]?\d+'
    elif symbType == 'type':
        regex = 'string|int|bool|float'

    if not re.fullmatch(regex, symb, re.DOTALL):
        print("Chybny argument", symb, regex)
        sys.exit(32)

#Pomocna funkce pro kontrolu argumentu
def argCheck(arg, argType):
    if 'type' not in arg.attrib or not re.fullmatch(argType, arg.attrib['type']):
        print("Chyba type")
        sys.exit(32)

    if arg.attrib['type'] == 'float':
        try:
            arg.text = float.hex(float.fromhex(arg.text))
        except:
            print("Zly float")
            sys.exit(32)

    symbCheck(arg.text, arg.attrib['type'])

#Funkce pro kontrolu instrukci
def instructionCheck(inst, args, argType = []):
    if len(inst) != args:
        print("Chybny pocet argumentu")
        sys.exit(32)
    for i in range(args):
        if inst[i].tag != 'arg' + str(i+1):
            print("Chybny tag parametru")
            sys.exit(32)
        argCheck(inst[i], argType[i])

#Funkce kontrolujici XML
def xmlCheck(xml):
    symb = 'var|int|string|bool|nil|float'
    for inst in xml:
        if 'opcode' not in inst.attrib:
            print("Chybi opcode")
            sys.exit(32)
        else:
            inst.attrib['opcode'] = inst.attrib['opcode'].upper()
        if re.fullmatch('(CREATE|POP|PUSH)FRAME|RETURN|BREAK', inst.attrib['opcode']):
            instructionCheck(inst, 0)
        elif re.fullmatch('(CLEAR|ADD|SUB|MUL|IDIV|LT|GT|EQ|AND|OR|NOT|INT2CHAR|STRI2INT)S', inst.attrib['opcode']):
            instructionCheck(inst, 0)
        elif re.fullmatch('DEFVAR|POPS', inst.attrib['opcode']):
            instructionCheck(inst, 1, ['var'])
        elif re.fullmatch('JUMP|CALL|LABEL|JUMPIFN?EQS', inst.attrib['opcode']):
            instructionCheck(inst, 1, ['label'])
        elif re.fullmatch('PUSHS|WRITE|DPRINT|EXIT', inst.attrib['opcode']):
            instructionCheck(inst, 1, [symb])
        elif re.fullmatch('MOVE|INT2CHAR|STRLEN|TYPE|NOT|INT2FLOAT|FLOAT2INT', inst.attrib['opcode']):
            instructionCheck(inst, 2, ['var', symb])
        elif re.fullmatch('ADD|SUB|MUL|I?DIV|LT|GT|EQ|AND|OR|STRI2INT|CONCAT|(G|S)ETCHAR', inst.attrib['opcode']):
            instructionCheck(inst, 3, ['var', symb, symb])
        elif re.fullmatch('JUMPIFN?EQ', inst.attrib['opcode']):
            instructionCheck(inst, 3, ['label', symb, symb])
        elif re.fullmatch('READ', inst.attrib['opcode']):
            instructionCheck(inst, 2, ['var', 'type'])
        else:
            print("Neznama instrukce")
            sys.exit(32)

#Pomocna funkce kontrolujici funkci pop ze zasovniku
def topPop(stack, error = 55):
    if len(stack) == 0:
        print("error, na zasobniku nejsou data")
        sys.exit(error)
    return stack.pop()

#Pomocna funkce kontrolujici funkci top nad zasobnikem
def top(stack):
    if len(stack) == 0:
        print("Chyba, na zasobniku nejsou data")
        sys.exit(55)
    return stack[-1]

#Pomocna funkce pro kontrolu mezi
def lenCheck(string, integer):
    if len(string) <= integer:
        print("Mimo meze stringu")
        sys.exit(58)
    return string[integer]

#Trida implementujici potrebne metody pro interpretaci kodu ipp2019
class ipp2019:
    var = dict()
    var['G'] = dict()
    var['T'] = list()
    var['L'] = list(dict())
    stack = list()
    labels = dict()
    fp = sys.stdin
    
    def __init__(self, xml, fp):
        for i in range(len(xml)):
            if xml[i].attrib['opcode'] == 'LABEL':
                if len(xml[i]) != 1 or xml[i][0].tag != 'arg1':
                    print("Chyba argumentu")
                    sys.exit(32)
                if xml[i][0].text in self.labels:
                    print("duplicitni label")
                    sys.exit(32)
                self.labels[xml[i][0].text] = i + 1
        self.fp = fp

    #Ziska ramec
    def getFrame(self, key):
        if key == 'G':
            return self.var['G']
        return top(self.var[key])

    #Premisti ramec
    def moveFrame(self, A, B):
        self.var[A].append(topPop(self.var[B]))

    #Zjisti existenci promenne a vrati ramec
    def varFrame(self, arg, statement = False):
        frame = self.getFrame(arg.text[0])
        if (arg.text[3:] in frame) == statement:
            print("Neexistujici promenna")
            sys.exit(54)
        return frame

    def move(self, inst, varType = '', value = ''):
        frame = self.varFrame(inst[0])
        if value == None:
            frame[inst[0].text[3:]] = [varType or str(inst[1].attrib['type']), '']
        else:
            frame[inst[0].text[3:]] = [varType or str(inst[1].attrib['type']), value or self.getValue(inst[1])[1]]

    def pops(self, inst):
        data = topPop(self.stack, 56)
        self.move(inst, data[0], data[1])

    def pushs(self, inst):
        self.stack.append(self.getValue(inst[0]))

    def defvar(self, arg):
        self.varFrame(arg, True)[arg.text[3:]] = None
    
    #Ziska promennou z ramce
    def getVar(self, arg, ctrl = True):
        frame = self.varFrame(arg)
        if frame[arg.text[3:]] == None and ctrl:
            print("Neinicializovana promenna")
            sys.exit(56)
        return frame[arg.text[3:]]

    #Ziska hodnotu argumentu (promenne ci konstanty)
    def getValue(self, arg, ctrl = True):
        if arg.attrib['type'] == 'var':
            return self.getVar(arg, ctrl)
        return [str(arg.attrib['type']), str(arg.text)]

    #Ziska hodnotu promenne ci konstanty a provede kontrolu
    def getValueCtrl(self, arg, ctrl, value = ".*", error = 53):
        var = self.getValue(arg)
        if not re.fullmatch(ctrl, var[0]) or not re.fullmatch(value, var[1], re.DOTALL):
            print("Spatna hodnota operandu", ctrl, var[0], value, var[1])
            sys.exit(error)
        return var[1]

    def strlen(self, inst):
        self.move(inst, 'int', str(len(str(self.getValueCtrl(inst[1], 'string')))))
  
    #zapise typ hodnoty do promenne jako string
    def varType(self, inst):
        if self.getValue(inst[1], False) == None:
            self.move(inst, 'string', self.getValue(inst[1], False))
        else:
            self.move(inst, 'string', self.getValue(inst[1], False)[0])
    
    def opNot(self, inst):
        self.move(inst, 'bool', str(self.getValueCtrl(inst[1], 'bool') == 'false').lower())

    def opAnd(self, inst):
        args = [self.getValueCtrl(inst[1], 'bool'), self.getValueCtrl(inst[2], 'bool')]
        self.move(inst, 'bool', str(args[0] == 'true' and args[1] == 'true').lower())
    
    def opOr(self, inst):
        args = [self.getValueCtrl(inst[1], 'bool'), self.getValueCtrl(inst[2], 'bool')]
        self.move(inst, 'bool', str(args[0] == 'true' or args[1] == 'true').lower())
    
    def add(self, inst):
        args = [self.getValueCtrl(inst[1], 'int|float'), self.getValueCtrl(inst[2], 'int|float')]
        vType = self.getValue(inst[1])[0]
        if vType != self.getValue(inst[2])[0]:
            print("Float a Int")
            sys.exit(53)
        if vType == 'float':
            self.move(inst, 'float', float.hex((float.fromhex(args[0]) + float.fromhex(args[1]))))
        else:
            self.move(inst, 'int', str(int(args[0]) + int(args[1])))
    
    def sub(self, inst):
        args = [self.getValueCtrl(inst[1], 'int|float'), self.getValueCtrl(inst[2], 'int|float')]
        vType = self.getValue(inst[1])[0]
        if vType != self.getValue(inst[2])[0]:
            print("Float a Int")
            sys.exit(53)
        if vType == 'float':
            self.move(inst, 'float', float.hex((float.fromhex(args[0]) - float.fromhex(args[1]))))
        else:
            self.move(inst, 'int', str(int(args[0]) - int(args[1])))
    
    def mul(self, inst):
        args = [self.getValueCtrl(inst[1], 'int|float'), self.getValueCtrl(inst[2], 'int|float')]
        vType = self.getValue(inst[1])[0]
        if vType != self.getValue(inst[2])[0]:
            print("Float a Int")
            sys.exit(53)
        if vType == 'float':
            self.move(inst, 'float', float.hex((float.fromhex(args[0]) * float.fromhex(args[1]))))
        else:
            self.move(inst, 'int', str(int(args[0]) * int(args[1])))
    
    def idiv(self, inst):
        args = [self.getValueCtrl(inst[1], 'int'), self.getValueCtrl(inst[2], 'int')]
        if args[1] == '0':
            print("Deleni nulou")
            sys.exit(57)
        self.move(inst, 'int', str(int(args[0]) // int(args[1])))
    
    def div(self, inst):
        args = [self.getValueCtrl(inst[1], 'float'), self.getValueCtrl(inst[2], 'float')]
        if float.fromhex(args[1]) == float(0):
            print("Deleni nulou")
            sys.exit(57)
        self.move(inst, 'float', float.hex(float.fromhex(args[0]) / float.fromhex(args[1])))
    
    #Vrati dvojici hodnot, pokud jsou kompatibilni
    def getCompatible(self, inst, A = 1, B = 2, nil = True):
        arg1 = self.getValue(inst[A])
        arg2 = self.getValue(inst[B])
        if (arg1[0] == arg2[0]) or (nil and (arg1[0] == 'nil' or arg2[0] == 'nil')):
            return [arg1, arg2]
        print("Nekompatibilni typy pro porovnani")
        sys.exit(53)
     
    def lt(self, inst, A = 1, B = 2):
        args = self.getCompatible(inst, A, B, False)
        if args[0][0] == 'int':
            self.move(inst, 'bool',  str(int(args[0][1]) < int(args[1][1])).lower())
        elif args[0][0] == 'float':
            self.move(inst, 'bool',  str(float.fromhex(args[0][1]) < float.fromhex(args[1][1])).lower())
        else:
            self.move(inst, 'bool',  str(args[0][1] < args[1][1]).lower())

    def gt(self, inst, A = 1, B = 2):
        self.lt(inst, B, A)

    def eq(self, inst, cond = True):
        args = self.getCompatible(inst, nil = cond)
        if cond:
            self.move(inst, 'bool', str(args[0] == args[1]).lower())
        return args[0] == args[1]

    def jump(self, label):
        if label not in self.labels:
            print("Neexistujici navesti")
            sys.exit(52)
        return int(self.labels[label]) - 2

    def jumpifeq(self, place, inst, cond = True):
        if self.eq(inst, False) == cond:
            return self.jump(inst[0].text)
        return place

    def jumpifneq(self, place, inst):
        return self.jumpifeq(place, inst, False)

    def read(self, inst):
        regex = '.*'
        if inst[1].text == 'int':
            regex = '[-+]?\d+'
        elif inst[1].text == 'bool':
            regex = '[tT][rR][uU][eE]'
        elif inst[1].text == 'float':
            regex = '[+-]?0x[01]\.[\da-fA-F]*p[+-]?\d+'
        load = self.fp.readline()
        if len(load) != 0 and load[-1] == '\n':
            load = load[:-1]
        
        if inst[1].text == 'int' and not re.fullmatch(regex, load.strip()):
            load = '0'
        elif inst[1].text == 'bool':
            if not re.fullmatch(regex, load.strip()):
                load = 'false'
            else:
                load = 'true'
        elif inst[1].text == 'float':
            if not re.fullmatch(regex, load.strip()):
                load = float.hex(float(0))
            else:
                load = float.hex(float.fromhex(load))
        if load == '':
            self.move(inst, inst[1].text, None)
        else:
            self.move(inst, inst[1].text, load)

    def concat(self, inst):
        self.move(inst, 'string', self.getValueCtrl(inst[1], "string") + self.getValueCtrl(inst[2], "string"))

    def stri2int(self, inst):
        var1 = self.getValueCtrl(inst[1], "string")
        value = lenCheck(self.getValueCtrl(inst[1], "string"), int(self.getValueCtrl(inst[2], "int")))
        self.move(inst, "int", str(ord(value)))

    def int2char(self, inst):
        value = int(self.getValueCtrl(inst[1], 'int'))
        if value < 0 or value > 1114111:
            print("chr musi byt v intervalu 0 - 1114111")
            sys.exit(58)
        self.move(inst, 'string', chr(value))

    def getchar(self, inst):
        value = lenCheck(self.getValueCtrl(inst[1], "string"), int(self.getValueCtrl(inst[2], "int")))
        self.move(inst, "string", value)
       
    def setchar(self, inst):
        var = list(self.getValueCtrl(inst[0], "string"))
        pos = int(self.getValueCtrl(inst[1], "int"))
        char = self.getValueCtrl(inst[2], "string")
        if len(char) == 0:
            print("Moc kratky string")
            sys.exit(58)
        lenCheck(var, pos)
        var[pos] = char[0]
        self.move(inst, "string", ''.join(var))

    def clears(self):
        self.stack = list()

    def adds(self):
        var2 = topPop(self.stack)
        var1 = topPop(self.stack)
        if var1[0] != var2[0] or (var1[0] != 'string' and var1[0] != 'int'):
            print("Nekompatibilni typy")
            sys.exit(53)
        if var1[0] == 'int':
            self.stack.append(['int', str(int(var1[1])+int(var2[1]))])
        elif var[0] == 'string':
            self.stack.append(['string', var1[1]+var2[1]])
        
    def subs(self):
        var2 = topPop(self.stack)
        var1 = topPop(self.stack)
        if var1[0] != 'int' or var2[0] != 'int':
            print("Nekompatibilni typy")
            sys.exit(53)
        self.stack.append(['int', str(int(var1[1])-int(var2[1]))])

    def muls(self):
        var2 = topPop(self.stack)
        var1 = topPop(self.stack)
        if var1[0] != 'int' or var2[0] != 'int':
            print("Nekompatibilni typy")
            sys.exit(53)
        self.stack.append(['int', str(int(var1[1])*int(var2[1]))])

    def idivs(self):
        var2 = topPop(self.stack)
        var1 = topPop(self.stack)
        if var1[0] != 'int' or var2[0] != 'int':
            print("Nekompatibilni typy")
            sys.exit(53)
        if var2[1] == '0':
            print("deleni nulou")
            sys.exit(57)
        self.stack.append(['int', str(int(var1[1])//int(var2[1]))])
    
    def lts(self):
        var2 = topPop(self.stack)
        var1 = topPop(self.stack)
        if var1[0] != var2[0] or var1[0] == 'nil':
            print("Nekompatibilni typy")
            sys.exit(53)
        if var1[0] == 'int':
            self.stack.append(['bool', str(int(var1[1])<int(var2[1])).lower()])
        else:
            self.stack.append(['bool', str(var1[1]<var2[1]).lower()])

    def gts(self):
        var2 = topPop(self.stack)
        var1 = topPop(self.stack)
        if var1[0] != var2[0] or var1[0] == 'nil':
            print("Nekompatibilni typy")
            sys.exit(53)
        if var1[0] == 'int':
            self.stack.append(['bool', str(int(var1[1])>int(var2[1])).lower()])
        else:
            self.stack.append(['bool', str(var1[1]>var2[1]).lower()])
    
    def eqs(self):
        var2 = topPop(self.stack)
        var1 = topPop(self.stack)
        if var1[0] != var2[0] and var2[0] != 'nil' and var1[0] != 'nil':
            print("Nekompatibilni typy")
            sys.exit(53)
        self.stack.append(['bool', str(var1[1] == var2[1] and var1[0] == var2[0]).lower()])
    
    def ands(self):
        var2 = topPop(self.stack)
        var1 = topPop(self.stack)
        if var1[0] != 'bool' or var2[0] != 'bool':
            print("Nekompatibilni typy")
            sys.exit(53)
        self.stack.append(['bool', str(var1[1] == 'true' and var2[1] == 'true').lower()])

    def ors(self):
        var2 = topPop(self.stack)
        var1 = topPop(self.stack)
        if var1[0] != 'bool' or var2[0] != 'bool':
            print("Nekompatibilni typy")
            sys.exit(53)
        self.stack.append(['bool', str(var1[1] == 'true' or var2[1] == 'true').lower()])

    def nots(self):
        var = topPop(self.stack)
        if var[0] != 'bool':
            print("Nekompatibilni typy")
            sys.exit(53)
        self.stack.append(['bool', str(var[1] == 'false').lower()])

    def int2chars(self):
        var = topPop(self.stack)
        if var[0] != 'int':
            print("Nekompatibilni typy")
            sys.exit(53)
        num = int(var[1])
        if num < 0 or num > 1114111:
            print("Nevalidni hodnota pro chr")
            sys.exit(58)
        self.stack.append(['bool', chr(num)])

    def stri2ints(self):
        var2 = topPop(self.stack)
        var1 = topPop(self.stack)
        if var2[0] != 'int' or var1[0] != 'string':
            print("Nekompatibilni typy")
            sys.exit(53)
        if len(var1[1]) <= int(var2[1]):
            print("Indexace mimo string")
            sys.exit(58)
        self.stack.append(['bool', str(ord(var1[1][int(var2[1])]))])

    def jumpifeqs(self, label, i):
        var2 = topPop(self.stack)
        var1 = topPop(self.stack)
        if var1[0] != var2[0]:
            print("Nekompatibilni typy")
            sys.exit(53)
        if var1[1] == var2[1]:
            return self.jump(label)
        return i

    def jumpifneqs(self, label, i):
        var2 = topPop(self.stack)
        var1 = topPop(self.stack)
        if var1[0] != var2[0]:
            print("Nekompatibilni typy")
            sys.exit(53)
        if var1[1] != var2[1]:
            return self.jump(label)
        return i

    def float2int(self, inst):
        value = self.getValueCtrl(inst[1], "float")
        self.move(inst, 'int', str(int(float.fromhex(value))))

    def int2float(self, inst):
        value = self.getValueCtrl(inst[1], "int")
        self.move(inst, 'float', float.hex(float(value)))

#Funkce implementujici interpretaci kodu ipp2019
def interpreter(xml, args, i = 0):
    retLine = list()
    count = 0
    fp = sys.stdin
    stats = None
    variables = 0
    #Nastaveni vstupu input
    if args['--input'] != '':
        try:
            fp = open(args['--input'], 'r')
        except:
            print("nelze otevrit soubor")
            sys.exit(11)
    #Nastaveni vystupu pro statistiky
    if args['--stats'] != '':
        try:
            stats = open(args['--stats'], 'w')
        except:
            print("nelze otevrit soubor")
            sys.exit(12)
    interpret = ipp2019(xml, fp)
    
    while i < len(xml):
        if xml[i].attrib['opcode'] == 'CREATEFRAME':
            interpret.var['T'].append(dict())
        elif xml[i].attrib['opcode'] == 'POPFRAME':
            interpret.moveFrame('T', 'L')
        elif xml[i].attrib['opcode'] == 'PUSHFRAME':
            interpret.moveFrame('L', 'T')
        elif xml[i].attrib['opcode'] == 'RETURN':
            i = topPop(retLine, 56)
        elif xml[i].attrib['opcode'] == 'DEFVAR':
            interpret.defvar(xml[i][0])
        elif xml[i].attrib['opcode'] == 'POPS':
            interpret.pops(xml[i])
        elif xml[i].attrib['opcode'] == 'JUMP':
            i = interpret.jump(xml[i][0].text)
        elif xml[i].attrib['opcode'] == 'CALL':
            retLine.append(i)
            i = interpret.jump(xml[i][0].text)
        elif xml[i].attrib['opcode'] == 'PUSHS':
            interpret.pushs(xml[i])
        elif xml[i].attrib['opcode'] == 'WRITE':
            write = interpret.getValue(xml[i][0])
            if write[0] != 'nil':
                print(write[1], end='')
        elif xml[i].attrib['opcode'] == 'EXIT':
            #Vypis statistik
            for key, value in args.items():
                if key == '--insts':
                    stats.write(str(count+1)+'\n')
                elif key == '--vars':
                    stats.write(str(variables)+'\n')
            code = int(interpret.getValueCtrl(xml[i][0], 'int')) 
            if code < 0 or code > 49:
                sys.exit(57)

            sys.exit(code)
        elif xml[i].attrib['opcode'] == 'MOVE':
            interpret.move(xml[i])
        elif xml[i].attrib['opcode'] == 'INT2CHAR':
            interpret.int2char(xml[i])
        elif xml[i].attrib['opcode'] == 'STRLEN':
            interpret.strlen(xml[i])
        elif xml[i].attrib['opcode'] == 'TYPE':
            interpret.varType(xml[i])
        elif xml[i].attrib['opcode'] == 'NOT':
            interpret.opNot(xml[i])
        elif xml[i].attrib['opcode'] == 'ADD':
            interpret.add(xml[i])
        elif xml[i].attrib['opcode'] == 'SUB':
            interpret.sub(xml[i])
        elif xml[i].attrib['opcode'] == 'MUL':
            interpret.mul(xml[i])
        elif xml[i].attrib['opcode'] == 'IDIV':
            interpret.idiv(xml[i])
        elif xml[i].attrib['opcode'] == 'DIV':
            interpret.div(xml[i])
        elif xml[i].attrib['opcode'] == 'LT':
            interpret.lt(xml[i])
        elif xml[i].attrib['opcode'] == 'GT':
            interpret.gt(xml[i])
        elif xml[i].attrib['opcode'] == 'EQ':
            interpret.eq(xml[i])
        elif xml[i].attrib['opcode'] == 'AND':
            interpret.opAnd(xml[i])
        elif xml[i].attrib['opcode'] == 'OR':
            interpret.opOr(xml[i])
        elif xml[i].attrib['opcode'] == 'STRI2INT':
            interpret.stri2int(xml[i])
        elif xml[i].attrib['opcode'] == 'CONCAT':
            interpret.concat(xml[i])
        elif xml[i].attrib['opcode'] == 'GETCHAR':
            interpret.getchar(xml[i])
        elif xml[i].attrib['opcode'] == 'SETCHAR':
            interpret.setchar(xml[i])
        elif xml[i].attrib['opcode'] == 'INT2FLOAT':
            interpret.int2float(xml[i])
        elif xml[i].attrib['opcode'] == 'FLOAT2INT':
            interpret.float2int(xml[i])
        elif xml[i].attrib['opcode'] == 'JUMPIFEQ':
            i = interpret.jumpifeq(i, xml[i])
        elif xml[i].attrib['opcode'] == 'JUMPIFNEQ':
            i = interpret.jumpifneq(i, xml[i])
        elif xml[i].attrib['opcode'] == 'READ':
            interpret.read(xml[i])
        elif xml[i].attrib['opcode'] == 'CLEARS':
            interpret.clears()
        elif xml[i].attrib['opcode'] == 'ADDS':
            interpret.adds()
        elif xml[i].attrib['opcode'] == 'SUBS':
            interpret.subs()
        elif xml[i].attrib['opcode'] == 'MULS':
            interpret.muls()
        elif xml[i].attrib['opcode'] == 'IDIVS':
            interpret.idivs()
        elif xml[i].attrib['opcode'] == 'LTS':
            interpret.lts()
        elif xml[i].attrib['opcode'] == 'GTS':
            interpret.gts()
        elif xml[i].attrib['opcode'] == 'EQS':
            interpret.eqs()
        elif xml[i].attrib['opcode'] == 'ANDS':
            interpret.ands()
        elif xml[i].attrib['opcode'] == 'ORS':
            interpret.ors()
        elif xml[i].attrib['opcode'] == 'NOTS':
            interpret.nots()
        elif xml[i].attrib['opcode'] == 'INT2CHARS':
            interpret.int2chars()
        elif xml[i].attrib['opcode'] == 'STRI2INTS':
            interpret.stri2ints()
        elif xml[i].attrib['opcode'] == 'JUMPIFEQS':
            i = interpret.jumpifeqs(xml[i][0].text, i)
        elif xml[i].attrib['opcode'] == 'JUMPIFNEQS':
            i = interpret.jumpifneqs(xml[i][0].text, i)

        count += 1
        i += 1
        #Prepocet inicializovanych promennych v existujicich ramcich
        active = len([x for x in interpret.var['G'] if interpret.var['G'][x] != None])
        if (len(interpret.var['T']) != 0):
            active += len([x for x in top(interpret.var['T']) if top(interpret.var['T'])[x] != None])
        for dictionary in interpret.var['L']:
            active += len([x for x in dictionary if dictionary[x] != None])
        if active > variables:
            variables = active
    #vypis statistik
    for key, value in args.items():
        if key == '--insts':
            stats.write(str(count)+'\n')
        elif key == '--vars':
            stats.write(str(variables)+'\n')

def main(argv):
    args = argParse(argv)
    xml = xmlParse(args['--source'])
    xmlCheck(xml)
    interpreter(xml, args)
    sys.exit(0)

main(sys.argv)
