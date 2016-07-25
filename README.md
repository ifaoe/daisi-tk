# daisi-tk
Service-Routinen zur Synchronisation von Sensordaten zur Bildakquise des digitalen Lufbilderfassungssytems am IfAÖ. 

# Namenkonventionen
<servercrunch> - Servername der 32 Kern Server mit hoher paralleler Rechenleistung (jalapeno in Rostock, tobasco in Hamburg)
<servergeo> - Servername des Servers welcher als Ziel für Geotiffs dienen soll (muss nach erforderlichem Platz ausgewählt werden "df -h" zeigt auch den Platz auf NFS Laufwerken an)
<serveriiq> - Servername des Servers welcher die IIQ enthält (in Rostock tandori, in Hamburg madras)
<servertif> - Servername des Servers welcher die unreferenzierten Tiffs enthält, bzw. enthalten soll (lediglich Zwischenspeicher also entweder tandori/madras oder <servergeo>)

###
## Erstellung der Datenbankgrundlage für einlaufende Flüge
###

Hinweis: Die Reihenfolge der Schritte muss unbedingt eingehalten werden.
Das Kopieren der IIQs von einer NTFS Festplatte mittels Linux auf die Windowsserver kann bei alten Linuxbversionen die Dateizeiten beschädigen (nur noch Sekunden Genauigkeit).
Daher sollten alle Logs direkt von den externen Platten erzeugt werden.

1. Erzeugen der Notwendigen GPS-Logs aus den Bildrohdaten:
1.1 Erzeugen der Ordnerstruktur
    - 
1.2 Erzeugen der Dateizeiten mittels Skript iiq-timestamps
    - iiq-timestamps erzeugt eine Liste von Dateizeit-Dateinamen Zuordnungen welche 

2. Kopieren der IIQs von Festplatte auf <serveriiq>

###
## Legacy Georeferenzierung
###

# IIQ zu tif Entwicklung
Auf allen Servern sollte das Dockerimage daisi-linco zu finden sein. Um sich nicht mit den Dockerargumenten rumschlagen zu müssen gibt es ein entsprechendes Wrapperscript run-linco.sh.
run-linco.sh benötigt 2 Argumente. Zum einen den Pfad zu den IIQs (/net/<serveriiq>/daisi/<projectname>/) und den Pfad in dem die tifs Zwischengespeichert werden sollen (/net/<servertif>/daisi/<projectname>/).
Dieser Befehl sollte entweder auf <servertif> oder auf <servercrunch> ausgeführt werden. Wobei die Ausführung auf <servercrunch> bevozugt werden sollte (schneller).

# Georeferenzierung
Checkliste:
1. Projekt ist in Datenbank eingetragen (nur die sync_utmXX wird benötigt)
2. Zielordner ist angelegt: mkdir -p /net/<servergeo>/<projektname>/cam{1,2}/geo
3. Notwendige Skripte in Projektverzeichnis verschieben (calc-geotiff-compressed, calc-parallel)
3.1 calc-geotiff-compressed anpassen 
    - $SESSION durch <projektname> ersetzen 
    - $DAISI_PATH durch /net/<servertif>/daisi ersetzen
    - $DAISI_OUT_PATH durch /net/<servergeo>/daisi ersetzen
3.2 calc-parallel anpassen 
    - $DAISI_PATH durch /net/<servertif>/daisi ersetzen
    - $DAISI_OUT_PATH durch /net/<servergeo>/daisi ersetzen
    
Ausführung:
Die einfache Ausführung von calc-parallel ohne Argumente wird eine entsprechende Anzahl an Threads zur Georeferenzierung starten. 
Der Befehl ist Fail-Safe. Auch bei fehlgeschlagenen Georeferenzierungen wird das Skript fortgesetzt.
 
Es ist normal,dass die ersten paar Referenzierungen fehlschlagen. Meistens sind dies Testbilder ohne korrektes GPS-Log dazu.
Sollte die Terminalausgabe jedoch durchgängige Fehlschläge anzeigen, dann kann mit STRG-C das Skript abgebrochen werden und anschließend (nach beheben des Fehlers) neu gestartet werden.

Hinweis: calc-parallel sucht nach bereits vorhanden Bildern und referenziert nur die Fehlenden Bilder nach. Sollte die Referenzierung allerdings ein korruptes GeoTiff produzieren, so kann mit dem
calc-geotiff-compressed Skript manuell ein einzelnes Bild nachreferenziert werden. Die Syntax lautet:
calc-geotiff-compressed <Kameranummer> <Bildname>
Hierfür muss das zuvor angepasste Skeript genutzt werden.
    
## Neue Georeferenzierung mittels Docker 
