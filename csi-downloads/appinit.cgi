#!/bin/sh
##############################################################
#
#   Generic 3rd party application initializer
#
#   this application handling will take care of integrating
#   third party applications in a generic non-intrusive way
#   Installing and Uninstalling is made easy by just
#   storing or removing a folder in the APPS_FOLDER
#   all subsequent configuration is done by inspecting
#   a configuration file in the application folder itself
#
#-------------------------------------------------------------
#
#   Version 0.1:
#       Ger Teunis: Initial version
#
#   Version 0.2:
#       Ger Teunis: Added auto-upgrade
#
#   Version 0.3
#       Ger Teunis: All files, including the script itself, should be stored in
#       profile folder.
#
#   Version 0.4
#       Ger Teunis: Fixed some small bug regarding creating items in crontab.
#
#   Version 0.5
#       Ger Teunis: Implemented Minimal AppInfo version
#
#   Version 0.6
#       Ger Teunis: Added the ability to install from tar or rar
#                   appinit will register itself on boot and start all applications
#                   implemented info; will be used by CSI for current statussen
#
#   Version 0.7
#       Ger Teunis: Renamed the script from .sh to .cgi and .appinfo folder to Appinfo
#                   this will allow the script being called by sybhttpd
#
#   Version 0.8
#       Ger Teunis: A lot of work has been done in fintuning the installation experience
#
#   Version 0.9
#       Ger Teunis: Refactoring and finetuning, needs more testing though.
#
#   Version 1.0
#       Ger Teunis: Added some more error messages
#
#   Version 1.1
#       Ger Teunis: Fixed bug where app names can't contain spaces
#                   Fixed backward compatability for old CSI when daemons are starting.
#
#   Version 1.2
#       Ger Teunis: Added restart
#
#   Version 1.3
#       Ger Teunis: Better compatibility with applicationnames containing spaces
#                   During install make sure symblic links are copied as well
#                   Store installation result in .setupresult in app folder
#
#   Version 1.4
#       Ger Teunis: Added ServerName back to appinit httpd.conf
#                   Better support for web applications.
#
#   Version 1.5
#       Ger Teunis: Optimized installing speed by extracting appinfo.json first
#                       and then extracting directly to the correct location
#                   Optimized a lot of string manipulations by using
#                       bash string manipulators instead of sed
#
#   Version 1.6
#       Ger Teunis: Added support for tar archive with files store in a "." folder
#
#   Version 1.7
#       Ger Teunis: Fixed a webservice remove and add bug, regression from
#                   optimalisations of version 1.5
#
#   Version 1.8
#       Ger Teunis: Fixed a bug causing the uninstall not to start correctly
#                   when performing an application upgrade
#
#   Version 1.9
#       Ger Teunis: Added cgi script capability to the appinit webserver
#                   Also strip tabs in front of parameters in appinfo.json
#
#   Version 1.10
#       Ger Teunis: Add support for 'real' JSON format
#                   Store daemon start result in .daemonresult during app start
#                   string_replace_all added, will replace all instances of string
#                   fixed a installation bug for applications containing spaces
#
#   Version 1.11
#       Ger Teunis: Fixed processing of appinfo.json parsing (start and comma)
#                   Added check if http.conf has invalid IP address configured
#                   Refactored the crontab functions
#
#   Version 1.12
#       Ger Teunis: Added state file and handling for stopping the AppInit http server
#                   This will allow 3rd party applications to replace the http server
#
#   Version 1.13
#       Ger Teunis: Set a fast timeout on version check, including 1 try instead of 20
#                   Always copy appinit to Profile, this will allow appinit upgrades
#                    via CSI when NMT has no correctly working internet connection.
#					Check if version length is 15 or less character
#					add .no_all.nmj to Apps folder so it will not be indexed
#
#   Version 1.14
#       jhmiller: Added support for SD Card and improved device detection
#
#   Version 1.15
#       jhmiller: Added improved device detection
#					
#
#-------------------------------------------------------------
#   Legal: published under GPL v3
#   http://www.gnu.org/licenses/gpl-3.0.txt
##############################################################






#--------------- VARIABLES ---------------

APPS_FOLDER="/share/Apps"
APPS_MINIMAL_APPINFO_VERSION="1"
APPINIT_NAME="Application Initializer"
APPINIT_FILENAME="appinit.cgi"
APPINIT_PROFILE="$APPS_FOLDER/AppInit"
APPINIT_VERSION="1.15"
APPINIT_VERSION_URL="http://54.75.246.28/csi-downloads/appinit_version"
APPINIT_UPGRADE_URL="http://54.75.246.28/csi-downloads/appinit.cgi"
APPINIT_AUTOSTART_STATE="/tmp/appinit_state"
APPINIT_WEBSERVER_DISABLED="/tmp/appinit_webserver_disabled"
CRONTAB_RELOAD="0"
APPINIT_APPS_AUTOSTART="0"
APPINIT_APPS_BOOTSTART="1"
TAR="/bin/tar"

#SET A400, 200/300 or A/B variables
echo -n "Found hardware type: "
if [ -e "/nmt/apps" ]; then
	NMTAPPS_LOCATION="/nmt/apps"
	STARTSCRIP_LOCATION="$NMTAPPS_LOCATION/etc/init_nmt"
	configid=$(genxenv2 l /tmp/lrro.xenv 2>/dev/null | grep -e " lrro.configid" | sed -e's/.*lrro.configid\s*//' | sed 's/\ //g'| sed 's/0x//g')
	configid=$configid[@]:0:4
	if [ "$configid" = "8911" ]; then
		echo "Popcorn Hour A-400"
	elif [ "$configid" = "8647" ]; then
		echo "Popcorn Hour A/C-300"
	else
		echo "Popcorn Hour A/C-200"
	fi
else
	echo "Popcorn Hour A-1xx/B-110"
	NMTAPPS_LOCATION="/mnt/syb8634"
	STARTSCRIP_LOCATION="$NMTAPPS_LOCATION/etc/ftpserver.sh"
fi

SCRIPTALIAS_LOCATION="$NMTAPPS_LOCATION/server"
HTTPDCONF_LOCATION="$NMTAPPS_LOCATION/server/php5server"
CRONTAB_LOCATION="$NMTAPPS_LOCATION/etc/root.cron"
UNRAR="$NMTAPPS_LOCATION/bin/unrar"




#--------------- APPINIT HELPER METHODS ---------------

appinit_auto_upgrade()
{
    echo -n "Checking for new version: "
    if [ ! -d "$APPINIT_PROFILE" ]; then
        mkdir -p "$APPINIT_PROFILE"
        chown nmt.nmt "$APPINIT_PROFILE"
    fi
    rm "$APPINIT_PROFILE/version_online" 2>/dev/null
    wget -T 3 -t 1 -q -O "$APPINIT_PROFILE/version_online" $APPINIT_VERSION_URL 2>/dev/null
    VERSION_ONLINE="`cat "$APPINIT_PROFILE/version_online"`"
    if [ -f "$APPINIT_PROFILE/version_online" ] && [ -n "$VERSION_ONLINE" ] && [ ${#VERSION_ONLINE} -lt 15 ] ; then
        if [ "$APPINIT_VERSION" != "`cat "$APPINIT_PROFILE/version_online"`" ]; then
            wget -q -O "$APPINIT_PROFILE/$APPINIT_FILENAME" $APPINIT_UPGRADE_URL
            echo "Upgraded"
            chmod a+x "$APPINIT_PROFILE/$APPINIT_FILENAME"
            chown nmt.nmt "$APPINIT_PROFILE/$APPINIT_FILENAME"
            eval "$APPINIT_PROFILE/$APPINIT_FILENAME \"$1\" \"$2\""
            exit 0
        else
           echo "up to date"
        fi
    else
        echo "Can't check for new version"
    fi
}

appinit_autostart_add()
{
    if [ -z "`cat "$CRONTAB_LOCATION" | grep "$APPINIT_FILENAME"`" ]; then
        echo "*/10 * * * * $APPINIT_PROFILE/$APPINIT_FILENAME start" >> "$CRONTAB_LOCATION"
        CRONTAB_RELOAD="1"
    fi
}

appinit_autostart_remove()
{
    if [ -n "`cat "$CRONTAB_LOCATION" | grep "$APPINIT_FILENAME"`" ]; then
        TEMP="`cat "$CRONTAB_LOCATION" | grep -v "$APPINIT_FILENAME"`"
        echo "$TEMP" > "$CRONTAB_LOCATION"
        CRONTAB_RELOAD="1"
    fi
}


appinit_bootstart_add()
{
    if [ -z "`cat "$STARTSCRIP_LOCATION" | grep "$APPINIT_FILENAME"`" ]; then
        echo -n "Configuring system to start all applications on boot: "
        TEMP="`cat "$STARTSCRIP_LOCATION"`"
        
        TEMP="`string_replace "$TEMP" "case \\\"\\$1\\\" in" "$APPINIT_PROFILE/$APPINIT_FILENAME \\\"\\$1\\\"
case \\\"\\$1\\\" in"`"
        
        echo "$TEMP" > "$STARTSCRIP_LOCATION"
        echo "Done"
    fi
}

appinit_bootstart_remove()
{
    if [ -n "`cat "$STARTSCRIP_LOCATION" | grep "$APPINIT_FILENAME"`" ]; then
        echo -n "Configuring system not to start all applications on boot: "
        TEMP="`cat "$STARTSCRIP_LOCATION" | grep -v "$APPINIT_FILENAME"`"
        echo "$TEMP" > "$STARTSCRIP_LOCATION"
        echo "Done"
    fi
}

appinit_profile_create()
{
    echo -n "Checking $APPINIT_NAME profile: "
    IP=`ifconfig | grep "inet addr"`
    IP=${IP#*:}
    IP=${IP%% *}
    
    #recreate if IP address has changed OR appinit profile folder doesn't exist OR
    #version file doesn't exists OR when the version number has changed
    if [ -z "`cat $APPINIT_PROFILE/httpd.conf | grep "ServerName $IP" 2>/dev/null`" ] || [ "`cat "$APPINIT_PROFILE/version" 2>/dev/null`" != "$APPINIT_VERSION" ] ; then
    
        if [ ! -d "$APPINIT_PROFILE" ]; then
            mkdir -p "$APPINIT_PROFILE"
            chown nmt.nmt "$APPINIT_PROFILE"
        fi

        #cleanup profile folder
        rm -Rf `ls -1 "$APPINIT_PROFILE" | grep -v "$APPINIT_FILENAME"` >/dev/null 2>&1

        if [ "$0" != "$APPINIT_PROFILE/$APPINIT_FILENAME" ]; then
            cp "$0" "$APPINIT_PROFILE/$APPINIT_FILENAME"
            rm -Rf "$0"
            chmod a+x "$APPINIT_PROFILE/$APPINIT_FILENAME"
            chown nmt.nmt "$APPINIT_PROFILE/$APPINIT_FILENAME"
        fi
        
        mkdir -p "$APPINIT_PROFILE/websites"
        chown nobody.99 "$APPINIT_PROFILE/websites"
        echo "$APPINIT_VERSION" > "$APPINIT_PROFILE/version"
        
        
        cat >"$APPINIT_PROFILE/httpd.conf" <<EOF
Port 9999
Listen 9999
<VirtualHost *:9999>
    ScriptAlias /php/ $SCRIPTALIAS_LOCATION/
    AddType application/x-httpd-php5 .php
    Action application/x-httpd-php5 /php/php5-cgi
    DocumentRoot $APPINIT_PROFILE/websites
    DirectoryIndex index.php index.cgi index.html
    ServerName $IP
</VirtualHost>

<Directory $APPINIT_PROFILE/websites>
    Options +ExecCGI
    AllowOverride All
    AddHandler cgi-script .cgi
</Directory>
EOF

        eval "$APPINIT_PROFILE/$APPINIT_FILENAME rescan"
        echo "Recreated"
    else
        echo "Valid"
    fi
    
    if [ ! -f "$APPS_FOLDER/.no_all.nmj" ]; then
    	touch "$APPS_FOLDER/.no_all.nmj"
    fi
}

appinit_profile_cronupdate()
{
    crontab -l > "$CRONTAB_LOCATION" 2>/dev/null
}

appinit_webserver_enable()
{
    rm -f "$APPINIT_WEBSERVER_DISABLED"

    TEST="`cat $HTTPDCONF_LOCATION/httpd.conf | grep "$APPINIT_PROFILE/httpd.conf"`"
    if [ -z "$TEST" ]; then
        echo -n "Enabling webserver: "
        escaped="`echo "$APPINIT_PROFILE" | sed "s/\\//\\\\\\\\\\//g"`"
        cp $HTTPDCONF_LOCATION/httpd.conf $HTTPDCONF_LOCATION/httpd_old.conf
        cat $HTTPDCONF_LOCATION/httpd_old.conf | \
            sed "s/Include httpd_inc.conf/Include httpd_inc.conf\nInclude $escaped\/httpd.conf/g" \
            >$HTTPDCONF_LOCATION/httpd.conf
        rm $HTTPDCONF_LOCATION/httpd_old.conf
 
        su -pm -c "cd $NMTAPPS_LOCATION/server && ./apachectl_php5 restart" nobody >/dev/null 2>&1
        echo "Done"
    fi
    
    #webserver is not running
    if [ -z "`ps | grep "/httpd -d $HTTPDCONF_LOCATION/" | grep -v "grep"`" ]; then
        su -pm -c "cd $NMTAPPS_LOCATION/server && ./apachectl_php5 restart" nobody >/dev/null 2>&1
    fi
}

appinit_webserver_disable()
{
    touch "$APPINIT_WEBSERVER_DISABLED"
    
    TEST="`cat $HTTPDCONF_LOCATION/httpd.conf | grep "$APPINIT_PROFILE/httpd.conf"`"
    if [ -n "$TEST" ]; then
       echo -n "Disabling webserver: "
       
       TEMP="`cat $HTTPDCONF_LOCATION/httpd.conf | grep -v "$APPINIT_PROFILE/httpd.conf"`"
       echo "$TEMP" > $HTTPDCONF_LOCATION/httpd.conf
    
       su -pm -c "cd $NMTAPPS_LOCATION/server && ./apachectl_php5 restart" nobody >/dev/null 2>&1
       echo "Done"
    fi
}






#--------------- APPLICATION HELPER METHODS ---------------

app_crontab_remove()
{
    if [ -n "`cat "$CRONTAB_LOCATION" | grep "#APPINIT_${name}#"`" ]; then
        TEMP="`cat "$CRONTAB_LOCATION" | grep -v "#APPINIT_${1}#" 2>/dev/null`"
        echo "$TEMP" > "$CRONTAB_LOCATION"
        CRONTAB_RELOAD="1"
    fi
}


app_crontab_add()
{
    if [ -n "$crontab" ] && [ -z "`cat "$CRONTAB_LOCATION" | grep "#APPINIT_${name}#"`" ]; then
        TEMP="`cat "$CRONTAB_LOCATION"`"
        TEMP="`string_replace "$TEMP" "#bt" "$crontab #APPINIT_${name}#
#bt"`"
        echo "$TEMP" > "$CRONTAB_LOCATION"
        CRONTAB_RELOAD="1"
    fi
}

app_websites_add()
{
    if [ -d "$webui_path" ] && [ ! -d "$APPINIT_PROFILE/websites/${name}_web" ]; then
        ln -s "$webui_path" "$APPINIT_PROFILE/websites/${name}_web"
    fi
    
    if [ -d "$gayaui_path" ] && [ ! -d "$APPINIT_PROFILE/websites/${name}_gaya" ]; then
        ln -s "$gayaui_path" "$APPINIT_PROFILE/websites/${name}_gaya"
        webservice_add "$name" "http://localhost:9999/${name}_gaya"
    fi
}

app_websites_remove()
{
    if [ -d "$APPINIT_PROFILE/websites/${name}_web" ]; then
        rm -Rf "$APPINIT_PROFILE/websites/${name}_web"
    fi
    
    if [ -d "$APPINIT_PROFILE/websites/${name}_gaya" ]; then
        rm -Rf "$APPINIT_PROFILE/websites/${name}_gaya"
        webservice_remove "$name" "http://localhost:9999/${name}_gaya"
    fi
}

app_fixpermissions()
{
    chown -R nmt.nmt "$1" >/dev/null 2>&1
    chmod -R 777 "$1" >/dev/null 2>&1
    chmod g+s "$1" >/dev/null 2>&1
}

app_daemon_execute()
{
    if [ -n "$daemon_script" ] && [ -f "$path/$daemon_script" ] ; then
        umask 0000
        cd "$path"
        eval "./$daemon_script \"$1\"" >"$path/.daemonresult" 2>&1
    fi
}

app_setup_execute()
{
    if [ -n "$1" ] && [ -n "$setup_script" ] && [ -f "$path/$setup_script" ]; then
        cd "$path"
        rm -f "$path/.setupresult"
        eval "./$setup_script \"$1\"" >>"$path/.setupresult" 2>>"$path/.setupresult"

        if [ "$1" == "install" ] && [ ! -f "$path/.installed" ]; then
            touch "$path/.installed"
        fi

        if [ "$1" == "uninstall" ] && [ -f "$path/.installed" ]; then
            rm -Rf "$path/.installed"
        fi
    fi
}

app_appinfo_parse()
{
    appinfo_format=""
    name=""
    version=""
    enabled="0"
    daemon_script=""
    path="${1%/*}/"
    crontab=""
    setup_script=""
    gayaui_path=""
    webui_path=""
    
    #explicit parsing of options
    #not using generic to prevent overwrite
    #of important vars or 
    #in case of using eval: security issues
    while read LINE ; do
        case "`parameter_name "$LINE"`" in
            appinfo_format)
            appinfo_format="`parameter_value "$LINE"`"
            ;;
            name)
            name="`parameter_value "$LINE"`"
            ;;
            version)
            version="`parameter_value "$LINE"`"
            ;;
            enabled)
            enabled="`parameter_value "$LINE"`"
            ;;
            daemon_script)
            daemon_script="`parameter_value "$LINE"`"
            ;;
            crontab)
            crontab="`parameter_value "$LINE"`"
            ;;
            setup_script)
            setup_script="`parameter_value "$LINE"`"
            ;;
            gayaui_path)
            gayaui_path="`parameter_value "$LINE"`"
            ;;
            webui_path)
            webui_path="`parameter_value "$LINE"`"
            ;;
        esac
    done < "$1"
}

app_autoinstall()
{
    if [ -n "$setup_script" ] && [ -f "$path/$setup_script" ] && [ ! -f "$path/.installed" ]; then
        app_setup_execute install
    fi
}

app_startstate_isstarted()
{
    if [ -n "`cat "$APPINIT_AUTOSTART_STATE" 2>/dev/null | grep "#${name}#"`" ]; then
        return 1
    else
        return 0
    fi
}

app_startstate_add()
{
    app_startstate_isstarted
    if [ "$?" == "0" ]; then
        echo "#${name}#" >> $APPINIT_AUTOSTART_STATE
    fi
}

app_startstate_remove()
{
    TEMP="`cat "$APPINIT_AUTOSTART_STATE"`"
    echo "$TEMP" | grep -v "#${name}#" > "$APPINIT_AUTOSTART_STATE"
}

app_enable()
{
    TEMP="`cat "$path/appinfo.json" | grep -v "enabled"`"
    TEMP="`string_replace "$TEMP" "{" "{
    enabled=\\\"1\\\","`"
    echo "$TEMP" > "$path/appinfo.json"
}

app_disable()
{
    TEMP="`cat "$path/appinfo.json" | grep -v "enabled"`"
    TEMP="`string_replace "$TEMP" "{" "{
    enabled=\\\"0\\\","`"
    echo "$TEMP" > "$path/appinfo.json"
}

app_install_fromfile()
{
    file="$1"
    if [ -z "`echo "$1" | grep "^/"`" ] && [ -f "/share/$1" ]; then
        file="/share/$1"
    fi
    
    if [ ! -f "$file" ]; then
        return 1
    fi

    echo -n "Installing application from file $file: "
    rm -Rf "$APPINIT_PROFILE/temp" >/dev/null 2>/dev/null
    mkdir -p "$APPINIT_PROFILE/temp"
    cd "$APPINIT_PROFILE/temp"
    
    #first we need only the appinfo
    #so we can uninstall the current version first
    case "`tolower "$file"`" in
        *.tar)
        eval "$TAR -x appinfo.json -vf \"$file\"" >/dev/null 2>/dev/null
        if [ ! -f "appinfo.json" ]; then
            eval "$TAR -x \"./appinfo.json\" -vf \"$file\"" >/dev/null 2>/dev/null
        fi
        ;;
        
        *.rar)  
        eval "$UNRAR x \"$file\" appinfo.json" >/dev/null 2>/dev/null
        if [ ! -f "appinfo.json" ]; then
            eval "$UNRAR x \"$file\" \"./appinfo.json\"" >/dev/null 2>/dev/null
        fi
        ;;
    esac
    
    if [ -f "$APPINIT_PROFILE/temp/appinfo.json" ]; then
        app_appinfo_parse "$APPINIT_PROFILE/temp/appinfo.json"
        path="$APPS_FOLDER/$name"

        if [ -d "$APPS_FOLDER/$name" ]; then
            echo -n "(and uninstalling current) "
            application_uninstall
        fi
        
        if [ ! -d "$APPS_FOLDER/$name" ]; then
            mkdir -p "$APPS_FOLDER/$name"
        fi

        #real untar to the desired location
        cd "$APPS_FOLDER/$name"
        
        case "`tolower "$file"`" in
            *.tar)
            eval "$TAR xvf \"$file\"" >/dev/null 2>/dev/null
            ;;
            
            *.rar)  
            eval "$UNRAR x -y \"$file\"" >/dev/null 2>/dev/null
            ;;
        esac
    fi

    rm -Rf "$APPINIT_PROFILE/temp" >/dev/null 2>/dev/null
    
    app_appinfo_parse "$APPS_FOLDER/$name/appinfo.json"
    
    if [ -n "$name" ]; then
        echo "Done"
    else
        echo "Failed"
        exit 1
    fi
}






#--------------- GENERIC HELPER METHODS ---------------

string_replace()
{
    STRING="$1"
    FIND="$2"
    REPLACE="$3"

    RIGHT="${STRING#*$FIND}"
    LEFT="${STRING%%$FIND*}"
    
    if [ "$LEFT" != "$STRING" ] && [ "$RIGHT" != "$STRING" ]; then
        STRING="${LEFT}${REPLACE}${RIGHT}"
    fi
    
    echo "${STRING}"
}

string_replace_all()
{
    STRING="$1"
    FIND="$2"
    REPLACE="$3"

    while [ "$COMPARE" != "$STRING" ]; do
        COMPARE="$STRING"
        RIGHT="${STRING#*$FIND}"
        LEFT="${STRING%%$FIND*}"
        
        if [ "$LEFT" != "$STRING" ] && [ "$RIGHT" != "$STRING" ]; then
            STRING="${LEFT}${REPLACE}${RIGHT}"
        fi
    done
    
    echo "${STRING}"
}

parameter_value()
{
    PAR="$1"
    PAR="${PAR#*=}"
    PAR="${PAR#*:}"
    PAR="${PAR%,*}"
    
    PAR="${PAR#*\"}"
    PAR="${PAR%\"*}"
    
    PAR="`string_replace "$PAR" "#PATH#" "$path"`"
    echo "$PAR"
}

parameter_name()
{
    PAR="$1"
    PAR="${PAR%=*}"
    PAR="${PAR%:*}"
    PAR="${PAR#*\"}"
    PAR="${PAR%\"*}"
    PAR="`string_replace_all "$PAR" " " ""`"
    PAR="`string_replace_all "$PAR" "   " ""`"
    
    echo "$PAR"
}

webservice_add()
{
    if [ -n "$1" -a -n "$2" ]; then
        url="$2"
        name="$1"
        webservice_remove "$name" "$url"
        
        #make url-nice, spaces to %20
        name_nice="`string_replace_all "$name" " " "%20"`"
        url_nice="`string_replace_all "$url" " " "%20"`"
        
        #Find a free id
        id=3
        test=`cat /opt/sybhttpd/default/webservices_edit.html | grep "option value=\"$id\""`
        while [ -n  "$test" ] && [ "$id" -le "13" ]; do
            id=$(( $id + 1 ))
            test=`cat /opt/sybhttpd/default/webservices_edit.html | grep "option value=\"$id\""`
        done
        
        if [ "$id" -le "12" ]; then
            #then add it again
            call="http://localhost:8883/webservices.cgi?%7Fadd=add&%7FhiDe=2&%7Faction=add&%7Fwebimg=&%7Fservlist=$id&_web_name_=$name_nice&_web_url_=$url_nice"
            wget -q -O - $call >/dev/null
        else
            echo "<b>ADDING WEBSERVICE FAILED</b><br><br>"
            echo "<h3>All ten positions already occuped</h3>Please remove a web service before adding one again."
        fi
    fi
}

webservice_remove()
{
    url="$2"
    name="$1"

    name_nice="`string_replace_all "$name" "%20" " "`"
    url_nice="`string_replace_all "$url" " " "%20"`"
    
    #first try to remove link, search by name
    id=`cat /opt/sybhttpd/default/webservices_edit.html | grep "option value=\"" | grep "$name_nice"`
    id=${id##*value=\"}
    id=${id%%\"*}
    call="http://localhost:8883/webservices.cgi?%7Fdel=remove&%7FhiDe=2&%7Faction=save&%7Fwebimg=&%7Fservlist=$id&_web_name_=$name&_web_url_=$url_nice"
    wget -q -O - $call >/dev/null
}

tolower()
{
    echo "$1" | sed "y/ABCDEFGHIJKLMNOPQRSTUVWXYZ/abcdefghijklmnopqrstuvwxyz/"
}

url_decode()
{
    url="$1"
    url="`string_replace_all "$url" "%2F" "/"`"
    url="`string_replace_all "$url" "%22" "\\\""`"
    url="`string_replace_all "$url" "%20" " "`"
    url="`string_replace_all "$url" "+" " "`"
    
    echo "$url"
}



#--------------- MAIN METHODS ---------------

application_start()
{
    echo -n "Starting $name: "
    app_startstate_isstarted
    if [ "$?" == "0" ]; then
        app_fixpermissions "$path"
        app_autoinstall
        app_websites_add
        app_crontab_add
        app_daemon_execute start
        app_startstate_add
        echo "Done"
    else
        echo "Already started"
    fi
}

application_stop()
{
    echo -n "Stopping $name: "
    app_startstate_isstarted
    if [ "$?" == "1" ]; then
        app_websites_remove
        app_crontab_remove "$name"
        app_daemon_execute stop
        app_startstate_remove
        echo "Done"
    else
        echo "Already stopped"
    fi
}

application_rescan()
{
    echo -n "Rescanning $name: "
    app_startstate_isstarted
    if [ "$?" == "1" ]; then
        app_websites_remove
        app_crontab_remove "$name"
        app_websites_add
        app_crontab_add
        echo "Done"
    else
        echo "Application not started"
    fi
}

application_uninstall()
{
    echo -n "Uninstalling $name: "

    app_crontab_remove "$name"
    app_websites_remove
    app_startstate_isstarted
    if [ "$?" == "1" ]; then
        app_daemon_execute stop
    fi
    app_startstate_remove
    app_setup_execute uninstall
    echo "Done"

}

application_enable()
{
    app_enable
}

application_disable()
{
    app_disable
}

application_info()
{
    TEMP="`cat "$path/appinfo.json"`"
    TEMP="`string_replace "$TEMP" "{" "{
    path=\\\"$path\\\","`"
    if [ -n "`cat "$APPINIT_AUTOSTART_STATE" 2>/dev/null | grep "$name"`" ]; then
        TEMP="`string_replace "$TEMP" "{" "{
    started=\\\"1\\\","`"
    else
        TEMP="`string_replace "$TEMP" "{" "{
    started=\\\"0\\\","`"
    fi
    echo "$TEMP"
}

application_install()
{
    app_install_fromfile "$1"
    
    if [ "$?" == "0" ]; then
        application_start
    else
        echo "Can't find file."
    fi
}

appinit_prepare()
{
    #appinit hookup and prepare
    appinit_auto_upgrade "$1" "$2"
    appinit_profile_create
    appinit_profile_cronupdate
    
    if [ -f "$APPINIT_WEBSERVER_DISABLED" ]; then
        appinit_webserver_disable
    else
        appinit_webserver_enable
    fi
    
    #and autostarts
    if [ "$APPINIT_APPS_AUTOSTART" == "1" ]; then
        appinit_autostart_add
    else
        appinit_autostart_remove
    fi
    
    if [ "$APPINIT_APPS_BOOTSTART" == "1" ]; then
        appinit_bootstart_add
    else
        appinit_bootstart_remove
    fi
}






#--------------- ENTRY LEVEL METHODS ---------------

process()
{
    ProcessedApplication="0"

    IFS=$(echo -en "\n\b")
    for appinfo in `ls -1d $APPS_FOLDER/*/appinfo.json 2>/dev/null`
    do
        app_appinfo_parse "$appinfo"
        
        if  [ "$APPS_MINIMAL_APPINFO_VERSION" -le "$appinfo_format" ]; then
            
            namelower="`tolower "$name"`"
            parameter="`tolower "$2"`"
                            
            #no second given means all
            #so name must be same as second parameter or no second parameter given
            if [ -z "$parameter" ] || [ "$parameter" == "$namelower" ]; then
            
                #In case of All applications do not process disabled applications
                if [ "$enabled" == "1" ] || [ -n "$2" ] || [ "$1" == "info" ]; then
                    
                    ProcessedApplication="1"
                    cd "$path"
                   
                    case "$1" in
                        start)
                        application_start
                        ;;
                        
                        stop)
                        application_stop
                        ;;
                        
                        restart)
                        application_stop
                        sleep 1
                        application_start
                        ;;
                        
                        rescan)
                        application_rescan
                        ;;
                        
                        uninstall)
                        application_uninstall
                        rm -Rf "$path"
                        ;;
                        
                        enable)
                        application_enable
                        ;;
                        
                        disable)
                        application_disable
                        ;;
                        
                        info)
                        application_info
                        ;;
                    esac
                else
                    application_stop
                fi
            fi
        fi
    done

    if [ -n "$2" ] && [ "$ProcessedApplication" == "0" ]; then
        echo "Unknown application"
    fi
}






#--------------- MAIN ---------------

echo
echo
echo "$APPINIT_NAME version $APPINIT_VERSION"
echo "---------------------------------------"

process="1"

#prepare appinit (integrate into NMT)
appinit_prepare "$1" "$2"

#Fix webcall parameters
if [ -n "$1" ] && [ -z "$2" ] && [ -n "`echo "$1" | grep "&"`" ]; then
    vars="`string_replace_all "${1}" "&" " "`"
    set `echo "$vars" `
fi

command="`url_decode "$1"`"
parameter="`url_decode "$2"`"

#Check command
case "$command" in
    install|uninstall|start|stop|restart|info|rescan|enable|disable|webserver_enable|webserver_disable)
    ;;
    
    *)
    echo
    echo "Usage: "
    echo "# $APPINIT_FILENAME {start|stop|restart|uninstall|rescan|enable|disable} [application name]"
    echo "    [application name] is not optional for some of these commands"
    echo "    this will control already installed applications."
    echo
    echo "# $APPINIT_FILENAME install {filename} (tar or rar)"
    echo "    This will install a application from tar or rar file."
    echo
    echo "# $APPINIT_FILENAME {webserver_enable|webserver_disable}"
    echo "    Will disable or enable the webserver used for applications"
    echo "    only to be used if another application is going to replace the webserver"
    echo
    echo "# $APPINIT_FILENAME info"
    echo "    Will display some systems stats, to be used by CSI."
    echo
    echo "ERROR: Invalid or no command given!"
    process="0"
    ;;
esac


# check number of parameters
if [ -z "$parameter" ]; then
    case "$command" in
        uninstall|enable|disable|install)
        echo "Invalid number of parameters, command $command requires two parameters"
        process="0"
        ;;
    esac
fi


if [ "$process" == "1" ]; then
    #in case of a special install command do not process via normal route
    case "$command" in
         install)
         application_install "$parameter"
         ;;
         
         webserver_enable)
         appinit_webserver_enable
         ;;
         
         webserver_disable)
         appinit_webserver_disable
         ;;
         
         *)
         process "$command" "$parameter"
         ;;
    esac
fi

#reload updated crontab
if [ "$CRONTAB_RELOAD" == "1" ]; then
    crontab "$CRONTAB_LOCATION"
    CRONTAB_RELOAD="0"
fi


#send EOF
echo
echo -e "\x04"
echo "</html>"