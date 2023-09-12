<?php
/**
 *
 * @author:     Radek Duchoň - xducho07
 * @created:    10.3.2019
 * @project:    IPPcode19
 * @file:       test.php
 *
 */
define("ERR_MISS", 10);
define("ERR_IN", 11);
define("ERR_OUT", 12);
define("ERR_SYS", 99);

//Pomocna funkce pro zpracovani argumentu a odhaleni kolizi
function arguments()
{
    $args = getopt('', ['directory:', 'recursive', 'parse-script:', 'int-script:', 'parse-only', 'int-only', 'help']);
    
    if (isset($args['int-only']) && isset($args['parse-only'])) {
        echo("Error: Neplatna kombinace argumentu.\n");
        die(ERR_MISS); 
    }
    
    if (isset($args['int-only']) && isset($args['parse-script'])) {
        echo("Error:Neplatna kombinace argumentu .\n");
        die(ERR_MISS); 
    }
    
    if (isset($args['parse-only']) && isset($args['int-script'])) {
        echo("Error: Neplatna kombinace argumentu.\n");
        die(ERR_MISS); 
    }
    
    if (isset($args['help'])) {
        global $argc;
        if ($argc != 2) {
            echo("Error: help s dalsim argumentem.\n");
            die(ERR_MISS);
        }
        echo("Napoveda - Skript pro automaticke otestovani skritů parse.php a interpret.py.\n");
        echo("Mozne argumenty jsou:\n\t--directory=\"file\" (volitelne nastaveni slozky s testy)\n\t");
        echo("--recursive (rekuzivni prohledavani lsozky s testy)\n\t");
        echo("--parse-script=\"file\" (volitelne nastaveni umisteni skriptu parse.php)\n\t");
        echo("--int-script=\"file\" (volitlene nastaveni umisteni skriptu interpret.pty)\n\t");
        echo("--parse-only (bude se testovat pouze skript parse.php)\n\t");
        echo("--int-only (bude se testovat pouze skript interpret.py)\n");
        exit(0);
    }
    
    if (!isset($args['parse-script']) && !isset($args['int-only']))
        $args['parse-script'] = 'parse.php';
    if (!isset($args['int-script']) && !isset($args['parse-only']))
        $args['int-script'] = 'interpret.py';
    if (!isset($args['directory']))
        $args['directory'] = getcwd();

    if (!isset($args['parse-only']) && !file_exists($args['int-script'])) {
        echo("Error: nelze nalezt interpret.py.\n");
        die(ERR_IN);
    }

    if (!isset($args['int-only']) && !file_exists($args['parse-script'])) {
        echo("Error: nelze nalezt parse.php.\n");
        die(ERR_IN);
    }
    
    return $args;
}

//Pomocna funkce, ktera zkontroluje existenci a pripadne dovytvori potrebne soubory k *.src
function make_files($src)
{
    global $files;
    array_push($files, $src);
    exec('touch '.$src.'.in');
    exec('touch '.$src.'.out');
    if (!file_exists($src.'.rc')) {
        if ($fp = fopen($src.'.rc', 'w')) {
            fwrite($fp, "0");
            fclose($fp);
        } else {
            echo("Error: Nelze vytvorit soubor.\n");
            die(ERR_IN);
        }
    }
    if (!file_exists($src.'.rc') || !file_exists($src.'.out') || !file_exists($src.'.in')){
        echo("Error: chybejici soubory se nepodarilo vytvorit.\n");
        die(ERR_IN);
    }
}

$args = arguments();
$xml = 'java -jar /pub/courses/ipp/jexamxml/jexamxml.jar ';
$options = ' /pub/courses/ipp/jexamxml/options';
$files = array();
$code = array();
$out = array();
$cnt = 0;

//Nacteni vsech zdrojovych souboru do pole $files - rekurzivni varianta
if (isset($args['recursive'])) {
    try {
        $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($args['directory']));
        foreach ($iterator as $info) {
            if (mb_ereg('.src$', $iterator->getFilename())) {
                make_files(mb_ereg_replace('.src$', '', $iterator->getPathName()));
            }
        }
    } catch (Exception $e) {
        echo("Error: Nelze otevrit slozku.\n");
        die(ERR_IN);
    }
//Nacteni vsech zdrojovych souboru do pole $files - nerekurzivni varianta
} elseif ($handle = @opendir($args['directory'])) {
    while (($entry = readdir($handle)) != false) {
        if (mb_ereg('.src$', $entry)) {
            make_files(mb_ereg_replace('.src$', '', $args['directory'].'/'.$entry));
        }
    }
    closedir($handle);
} else {
    echo("Error: Nelze otevrit slozku.\n");
    die(ERR_IN);
}

//generovani nekolizniho jmena souboru a jeho vytvoreni
$dif = 'a';
while (file_exists($dif.'.xml') || file_exists($dif.'.xml.log'))
    $dif = $dif.'a';
$dif = $dif.'.xml';

if ($fp = fopen($dif, 'w+'))
    fclose($fp);
else {
    echo("Error: Nepodarilo se vytvorit docasny soubor.\n");
    die(ERR_OUT);
}

echo("<!DOCTYPE html>\n<html>\n<body>\n<table style=\"width:100%\">\n");
echo("<tr bgcolor=#bbb>\n<th>Test</th>\n<th>Output</th>\n<th>Code</th>\n</tr>\n");

if (isset($args['parse-only'])) {
    //Zpracovavani pomoci foreach pro kazdy zdrojovy soubor *.src
    foreach ($files as $key => $value) {
        echo("<tr bgcolor=#bbb>\n<td bgcolor=");
        exec('php7.3 '.$args['parse-script'].' < '.$value.'.src > '.$dif, $out, $code[0]);
        $num = trim(file_get_contents($value.'.rc'));
        
        if ($num != $code[0]) {
            echo("red>".$value."</td>\n<td></td>\n<td bgcolor=red>".$code[0]."/".$num."</td>\n");
        } elseif ($code[0] == 0) {
            exec($xml.$dif .' '.$value.'.out '.$dif.$options, $out, $code[1]);
            
            if ($code[1] != 0)
                echo("red>".$value."</td>\n<td bgcolor=red>Not same</td>\n<td bgcolor=green>0/0</td>\n");
            else {
                echo("green>".$value."</td>\n<td bgcolor=green>Same</td>\n<td bgcolor=green>0/0</td>\n");
                $cnt++;
            }
        } else {
            echo("green>".$value."</td>\n<td bgcolor=green>Nothing</td>\n<td bgcolor=green>".$code[0]."/".$code[0]."</td>\n");
            $cnt++;
        }

        echo("</tr>\n");
    }
} elseif (isset($args['int-only'])) {

} else {
    //Zpracovavani pomoci foreach pro kazdy zdrojovy soubor *.src
    foreach ($files as $key => $value) {
        echo("<tr bgcolor=#bbb>\n<td bgcolor=");
        exec('php7.3 '.$args['parse-script'].' < '.$value.'.src > '.$dif, $out, $code[0]);
        $num = trim(file_get_contents($value.'.rc'));
        
        if ($code[0] != 0) {
            if ($num == $code[0]) {
                echo("green>".$value."</td>\n<td bgcolor=green>Nothing</td>\n<td bgcolor=green>".$code[0]."/".$code[0]."</td>\n");
                $cnt++;
            } else
                echo("red>".$value."</td>\n<td></td>\n<td bgcolor=red>".$code[0]."/".$num."</td>\n");
        } else {
            exec('python3.6 '.$args['int-script'].' --input='.$value.'.in --source='.$dif, $out, $code[0]);
            $fp = fopen($dif, 'w');
            foreach ($out as $k => $v)
                fwrite($fp, $v."\n");
            
            if ($num == $code[0]) {
                exec('diff '.$dif.' '.$value.'.out', $out, $code[0]);
                
                if ($code[0] == 0) {
                    echo("green>".$value."</td>\n<td bgcolor=green>Nothing</td>\n<td bgcolor=green>".$code[0]."/".$code[0]."</td>\n");
                    $cnt++;
                } else
                    echo("red>".$value."</td>\n<td bgcolor=red>Not same</td>\n<td bgcolor=green>0/0</td>\n");
            } else
                echo("red>".$value."</td>\n<td></td>\n<td bgcolor=red>".$code[0]."/".$num."</td>\n");
        }
        
        echo("</tr>\n");
    }
}

echo("</table>\n<br>\n");
if ($cnt == sizeof($files))
    echo("<font color=\"green\">".$cnt."/".$cnt."</font>\n");
else
    echo("<font color=\"red\">".$cnt."/".sizeof($files)."</font>\n");

echo("</body>\n</html>\n");
exec('rm '.$dif.' '.$dif.'.log');
?>
