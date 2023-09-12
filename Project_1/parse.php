<?php
/**
 *
 * @author:     Radek Duchoň - xducho07
 * @created:    4.3.2019
 * @project:    IPPcode19
 * @file:       parse.php
 *
 */
define("ERR_MISS", 10);
define("ERR_OUT", 12);
define("ERR_HEADER", 21);
define("ERR_UNKNOWN", 22);
define("ERR_OTHER", 23);

//veskere slozitejsi regularni vyrazy potrebne v tomto skriptu
define("_LABEL", '([_a-zA-Z-$&%*?!][_a-zA-Z-$&%*?!\d]*)');
define("_VAR", '((L|G|T)F@'._LABEL.')');
define("_BOOL", '(bool@(true|false))');
define("_INT", '(int@[-+]?\d+)');
define("_STRING", '(string@(([^\s\\\\#])|(\\\\\d{3}))*)');
define("_NIL", '(nil@nil)');
define("_SYMB", '('._BOOL.'|'._INT.'|'._STRING.'|'._NIL.'|'._VAR.')');

//Pro zjisteni, zda je nastavena nejaka statisticka hodnota ke sberu - nesmi, pokud neni zadan i argument --stats="file"
function args_ctrl($args)
{
    return isset($args['loc']) || isset($args['comments']) || isset($args['labels']) || isset($args['jumps']);
}

//Pomocna funkce pro nacteni argumentu
function arguments()
{
    $args = getopt('', ['stats:', 'loc', 'comments', 'labels', 'jumps', 'help']);
    
    if (!isset($args['stats']) && args_ctrl($args)) {
        echo("Error: Nepovolena kombinace argumentu.\n");
        die(ERR_MISS); 
    }
    if (isset($args['help'])) {
        global $argc;
        if ($argc != 2) {
            echo("Error: Help nelze kombinovat s argumenty.\n");
            die(ERR_MISS);
        }
        echo("Napoveda:\nSkript vytvari XML z IPPcode19.\mSpustte a zadejte kod na standardni vstup.\n");
        echo("Je mozno zadat argument --stats=\"file\" pro ukladani statistik.\n");
        echo("Mozne argumenty pro statistiky jsou:\n\t --loc (pocet instrukci)\n\t");
        echo("--comments (pocet radku s komentarem)\n\t");
        echo("--labels (pocet univerzalnich navesti)\n\t");
        echo("--jumps (pocet skokovych instrukci)\n");
        exit(0);
    }
    return $args;
}

//Pomocna funkce pro kontrolu argumentu
function konec($instruct, $num)
{
    if ($instruct[$num] != '') {
        echo("Error: Neplatny argument instrukce.\n");
        die(ERR_OTHER);
    }
}

//Pomocna funkce pro zpracovani jednoho argumentu instrukce
function arg($instruct, $match, $arg = 1, $ctrl = 0)
{
    global $xml;
    $type;

    if($ctrl != 0)
        konec($instruct, $arg+1);
    
    if (!mb_ereg('^'.$match.'$', $instruct[$arg])) {
        echo("Error: Neplatny argument instrukce.\n");
        die(ERR_OTHER);
    }

    //Postupna kontrola o jaky typ argumentu se jedna
    if (mb_ereg('^'._VAR, $instruct[$arg])) {
        $type = 'var';
    } elseif (mb_ereg('^'._INT, $instruct[$arg])) {
        $type = 'int';
        $instruct[$arg] = substr($instruct[$arg], 4);
    } elseif (mb_ereg('^'._BOOL, $instruct[$arg])) {
        $type = 'bool';
        $instruct[$arg] = substr($instruct[$arg], 5);
    } elseif (mb_ereg('^'._NIL, $instruct[$arg])) {
        $type = 'nil';
        $instruct[$arg] = substr($instruct[$arg], 4);
    } elseif (mb_ereg('^'._STRING, $instruct[$arg])) {
        $type = 'string';
        $instruct[$arg] = substr($instruct[$arg], 7);
    } else
        $type = 'label';

    $xml->startElement('arg'.$arg);
    $xml->writeAttribute('type', $type);
    $xml->text($instruct[$arg]);
    $xml->endElement();
}

//funkce pro zpracovani jednoho radku
function process($line)
{
    global $xml;
    global $loc;
    global $jumps;
    global $labels;
    static $order = 1;
    static $label_list = array();
    
    if ($line == '')
        return;
    
    $loc++;
    $instruct = explode(' ', mb_ereg_replace('[\ \t]+', ' ', $line));

    $xml->startElement('instruction');
    $xml->writeAttribute('order', $order++);
    $xml->writeAttribute('opcode', strtoupper($instruct[0]));

    //Postupna snaha odhalit instrukci. Instrukce jsou rozdeleny do skupin dle jejich argumentu, pripadne josu odeleny pro ucely statistiky
    if (mb_eregi('^((CREATE|POP|PUSH)FRAME|RETURN|BREAK)$', $instruct[0])) {
        konec($instruct, 1);
    } elseif (mb_eregi('^(DEFVAR|POPS)$', $instruct[0])) {
        arg($instruct, _VAR, 1, 1);
    } elseif (mb_eregi('^(CALL)$', $instruct[0])) {
        arg($instruct, _LABEL, 1, 1);
    } elseif (mb_eregi('^(LABEL)$', $instruct[0])) {
        if (!isset($label_list[$instruct[1]])) {
            $label_list[$instruct[1]] = false;
            $labels++;
        }
        arg($instruct, _LABEL, 1, 1);
    } elseif (mb_eregi('^(JUMP)$', $instruct[0])) {
        $jumps++;
        arg($instruct, _LABEL, 1, 1);
    } elseif (mb_eregi('^(PUSHS|WRITE|DPRINT|EXIT)$', $instruct[0])) {
        arg($instruct, _SYMB, 1, 1);
    } elseif (mb_eregi('^(MOVE|INT2CHAR|STRLEN|TYPE|NOT)$', $instruct[0])) {
        arg($instruct, _VAR);
        arg($instruct, _SYMB, 2, 1);
    } elseif (mb_eregi('^(ADD|SUB|MUL|IDIV|LT|GT|EQ|AND|OR|STRI2INT|CONCAT|(G|S)ETCHAR)$', $instruct[0])) {
        arg($instruct, _VAR);
        arg($instruct, _SYMB, 2);
        arg($instruct, _SYMB, 3, 1);
    } elseif (mb_eregi('^(JUMPIFN?EQ)$', $instruct[0])) {
        $jumps++;
        arg($instruct, _LABEL);
        arg($instruct, _SYMB, 2);
        arg( $instruct, _SYMB, 3, 1);
    } elseif (mb_eregi('^(READ)$', $instruct[0])) {
        arg($instruct, _VAR);
        $xml->startElement('arg2');
        $xml->writeAttribute('type', 'type');
        if (!mb_eregi('^(int|bool|string)$', $instruct[2])) {
            echo("Error: chybny argument.\n");
            die(ERR_OTHER);
        }
        $xml->text($instruct[2]);
        $xml->endElement();
        konec($instruct, 3);
    } else {
        echo("Error: Chybna instrukce.");
        die(ERR_UNKNOWN);
    }

   $xml->endElement();
}

$args = arguments();
//Nacteni a zpracovani hlavicky
if (strcasecmp(trim(explode('#', fgets(STDIN))[0]), '.IPPcode19')) {
    echo("Error: Chybna hlavicka.\n");
    die(ERR_HEADER);
}

$xml = new XMLWriter();
$xml->openMemory();
$xml->setIndent(true);

$xml->startDocument('1.0', 'UTF-8');
$xml->startElement('program');
$xml->writeAttribute('language', 'IPPcode19');

$line;
//inicilaizace promennych pro statistiky
$loc = 0;
$comments = 0;
$jumps = 0;
$labels = 0;

//postupne zpracovavani vstupu po jednom radku
while (($line = fgets(STDIN)) != false){
    if($line != explode('#', $line)[0])
        $comments++;
    process(trim(explode('#', $line)[0]));
}

$xml->endElement();

//zapis statistik dle poradi argumentu
if (isset($args['stats'])) {
    $fp = fopen($args['stats'], 'w');
    if ($fp == false)
        die(ERR_OUT);

    foreach ($args As $key => $value) {
        if ($key != 'stats') {
            fwrite($fp, $$key."\n");
        }
    }
    fclose($fp);
}

echo($xml->flush());
?>
