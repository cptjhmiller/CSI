#!/bin/sh

########### VARIABLES ########### 
if [ -d "/opt/sybhttpd/localhost.drives/HARD_DISK" ] && [ ! -L "/opt/sybhttpd/localhost.drives/HARD_DISK" ]; then
	HDD="HARD_DISK"
elif [ -d "/opt/sybhttpd/localhost.drives/SATA_DISK" ] && [ ! -L "/opt/sybhttpd/localhost.drives/HARD_DISK" ]; then
	HDD="SATA_DISK"
elif [ -d "/opt/sybhttpd/localhost.drives/USB_DRIVE" ] && [ ! -L "/opt/sybhttpd/localhost.drives/HARD_DISK" ]; then
	HDD="USB_DRIVE"
elif [ -d "/opt/sybhttpd/localhost.drives/USB_DRIVE_SD_CARD" ] && [ ! -L "/opt/sybhttpd/localhost.drives/HARD_DISK" ]; then
	HDD="USB_DRIVE_SD_CARD"
fi

STARTER="/share/start_app.sh"
MARKER="#M_A_R_K_E_R_do_not_remove_me"
WAITIMAGES="/share/Photo/_waitimages_"

#SET A400, 200/300 or A/B variables
echo -n "Found hardware type: "
if [ -e "/nmt/apps" ]; then
	NMTAPPS_LOCATION="/nmt/apps"
	STARTSCRIP_LOCATION="$NMTAPPS_LOCATION/etc/init_nmt"
	configid=$(genxenv2 l /tmp/lrro.xenv 2>/dev/null | grep -e " lrro.configid" | sed -e's/.*lrro.configid\s*//' | sed 's/\ //g'| sed 's/0x//g')
	configid=$configid[@]:0:4
	if [ "$configid" = "8003" ]; then
		echo "Popcorn Hour VTEN"
	elif [ "$configid" = "8911" ]; then
		echo "Popcorn Hour A400/410"
	elif [ "$configid" = "8647" ]; then
		echo "Popcorn Hour A/C300"
	else
		echo "Popcorn Hour A/C200"
	fi
else
	echo "Popcorn Hour A1xx/B110"
	NMTAPPS_LOCATION="/mnt/syb8634"
	STARTSCRIP_LOCATION="$NMTAPPS_LOCATION/etc/ftpserver.sh"
fi

IFS='&'
for i in $1; do
    eval "$i"
done
unset IFS
########### VARIABLES ###########



script_b110_compatibility()
{
    echo '
#For some NMT hardware (like Popcorn B-110) compatibility may go up when creating a
#symbolic link HARD_DISK to SATA_DISK
if [ ! -d "/opt/sybhttpd/localhost.drives/HARD_DISK" ]; then
    ln -s /opt/sybhttpd/localhost.drives/'$HDD' /opt/sybhttpd/localhost.drives/HARD_DISK
fi
 
'
}

script_copy_waitimages()
{
    echo '
#Copy waitimages when they are available
if [ -n "`ls -Al /share/Photo/_waitimages_/*.jpg 2>/dev/null`" ]; then
    cp /share/Photo/_waitimages_/* /bin
fi
 
'
}

script_cleanup()
{
    echo '
#cleanup old files
rm -f /share/busybox 2>&1 >/dev/null
rm -f /share/commands.cgi 2>&1 >/dev/null


'
}

script_header()
{
    echo '#!/bin/sh
#

PATH=/share/Apps/Telnetd/bin:/share/bin:/share/Apps/AppInit:$PATH
HOME=/share
export TERM="xterm"
alias mc="mc -c"
 
'
}

script_footer()
{
    echo '
exit 0'
}

compile_script()
{
    COMPILE=$(script_header)
    COMPILE=$COMPILE$(script_copy_waitimages)
    COMPILE=$COMPILE$(script_b110_compatibility)
    COMPILE=$COMPILE$(script_cleanup)
    
    rm -f /tmp/.starter.tmp
    echo "$COMPILE" > /tmp/.starter.tmp
    echo "$MARKER" >> /tmp/.starter.tmp
    
    #Add the already added programs
    SKIP=1
    IFS=""
    cat "$STARTER" 2>/dev/null | {
    while read line ;
    do
        if [ "$SKIP" == "0" ]; then
            if [ "$line" != "exit 0" ]; then
                if [ -n "$line" ]; then
                    echo "$line" >> /tmp/.starter.tmp
                fi
            fi
        fi
        
        if [ x"$line" == x"$MARKER" ]; then
            SKIP="0"
        fi
    done;}

    #Add parameter one if not already added
    if [ -n "$1" ]; then 
        if [ -z `cat /tmp/.starter.tmp | grep "$1"` ]; then
                echo "Configuring system to start application on startup: Done<br>"
                echo "$1" >> /tmp/.starter.tmp
        fi
    fi
    
    echo "$(script_footer)" >> /tmp/.starter.tmp
    
    cp /tmp/.starter.tmp /share/start_app.sh
    rm -f /tmp/.starter.tmp
    chmod 777 /share/start_app.sh
}

hookup_script()
{
    grep -q "$STARTER" "$STARTSCRIP_LOCATION"
    if [ $? != 0 ]; then
        cp "$STARTSCRIP_LOCATION" "$STARTSCRIP_LOCATION.backup"
        
        rm -f /tmp/.integrate.tmp /tmp/.found
        IFS=""
        cat "$STARTSCRIP_LOCATION" | grep -v "start_app" | while read line
            do
            echo "$line" >> /tmp/.integrate.tmp
            if [ x"$line" == x"start() {" ]; then
                echo "        $STARTER &" >> /tmp/.integrate.tmp
            fi
        done

        cat < /tmp/.integrate.tmp > "$STARTSCRIP_LOCATION"
        chmod 774 "$STARTSCRIP_LOCATION"
        rm -f /tmp/.integrate.tmp
    fi
}

add_webservice()
{
    if [ -n "$1" -a -n "$2" ]; then
        echo -n "Adding a new web service: "
        
        url="$2"
        name="$1"
        name_nice=`echo "$name" | sed 's/%20/ /g'`
        
        #first try to remove link, search by name
        id=`cat /opt/sybhttpd/default/webservices_edit.html | grep "option value=\"" | grep "$name_nice" | sed 's/.*"\([0-9]\)".*/\1/g'`
        call="http://localhost:8883/webservices.cgi?%7Fdel=remove&%7FhiDe=2&%7Faction=save&%7Fwebimg=&%7Fservlist=$id&_web_name_=$name&_web_url_=$url"
        wget -q -O - $call >/dev/null
        
        #Find a free id
        id=3
        test=`cat /opt/sybhttpd/default/webservices_edit.html | grep "option value=\"$id\""`
        while [ -n  "$test" ] && [ "$id" -le "13" ]; do
            id=$(( $id + 1 ))
            test=`cat /opt/sybhttpd/default/webservices_edit.html | grep "option value=\"$id\""`
        done
        
        if [ "$id" -le "12" ]; then
            #then add it again
            call="http://localhost:8883/webservices.cgi?%7Fadd=add&%7FhiDe=2&%7Faction=add&%7Fwebimg=&%7Fservlist=$id&_web_name_=$name&_web_url_=$url"
            wget -q -O - $call >/dev/null
        
            echo "Done<br>"
        else
            echo "<b>FAILED</b><br><br>"
            echo "<h3>All ten positions already occuped</h3>Please remove a web service before adding one again."
        fi
    fi
}

rollout_appinit()
{
    if [ ! -f "/share/Apps/AppInit/appinit.cgi" ]; then
        wget -T 3 -q -O /share/appinit.cgi http://54.75.246.28/~csi/csi-downloads/appinit.cgi >/dev/null 2>/dev/null
        
        if [ -f "/share/appinit.cgi" ]; then
            chmod a+x /share/appinit.cgi
            eval "/share/appinit.cgi >/dev/null 2>/dev/null"
        fi
    fi
}


compile_script "$autostart_add"
add_webservice "$webservice_name" "$webservice_url"
hookup_script
eval $(script_copy_waitimages)
eval $(script_b110_compatibility)
eval $(script_cleanup)
rollout_appinit
