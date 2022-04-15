#!/bin/bash

#Copyright (c) 2008-2011 VMware, Inc.  All rights reserved. 
#
# convert a directory to an rpm or debian package containing that layout
#

BUILD_DIR=.build
BUILD_PATH=$PWD/$BUILD_DIR
DEBIAN_DIR=$BUILD_DIR/DEBIAN
POSTINST=postinst
PREINST=preinst
POSTRM=postrm
PRERM=prerm
SOURCE_DIR=
HSPEC=.config.spec
DEB_CONTROL=control
RPM_CONTROL=control.spec
CONFFILES=conffiles
CONTROL=
TYPE=
template=0

trap "rm -rf $BUILD_DIR; exit 1" 1 2 3 14 15

                                
stderr()
{
    /bin/echo -e "$*" 1>&2
}

longusage()
{
    usage
    stderr
    stderr '\t -t \tType of package to create (rpm, rpm64, or deb).'
    stderr
    stderr '\t -T \tA sample control file to be used as a template will be'
    stderr '\t    \tcreated for the package type.'
    stderr
    stderr '\t -c \tPackage control file. A sample control file to be'
    stderr '\t    \tused as a template can be created by using the -T'
    stderr '\t    \toption.'
    stderr
    stderr '\t -C \tFile ontaining a list of user configuration files'
    stderr '\t    \tthat will not be overwritten when package is upgraded.'
    stderr
    stderr '\t -P \tPre-installation script to be run before the package'
    stderr '\t    \tis installed.'
    stderr
    stderr '\t -p \tPost-installation script to be run after the package'
    stderr '\t    \tis installed.'
    stderr
    stderr '\t -R \tPre-removal script to be run before the package'
    stderr '\t    \tis removed.'
    stderr
    stderr '\t -r \tPost-removal script to be run after the package is'
    stderr '\t    \tremoved.'
    stderr
    stderr '\t dir\tDirectory to be packaged. Programs and files in this'
    stderr '\t    \tdirectory should be in their proper place when'
    stderr '\t    \tinstalled, relative to this directory. For example,'
    stderr '\t    \ta file that should be installed into the /etc directory'
    stderr '\t    \tshould be put into a subdirectory called etc in the'
    stderr '\t    \tsupplied directory.'
}

usage()
{
    stderr "Usage: $pgm -t {rpm|rpm64|deb} [-T] [-c control] [-C conffiles] [-P preinst] [-p postinst] [-R prerem] [-r postrem] [-H|-h] dir"
}

#
# Make a template packaging control file
#
# $1 == package type
# $2 == filename to create
#
make_template()
{    
     if [ -f $2 ]
     then
        stderr $pgm: will not overwrite existing file \"$2\"
        return 1
     fi

    case "$1" in
        rpm|rpm64)
            (
            echo Summary: This is the short description of the package.
            echo Name: change-this-package-name
            echo Version: 99.99
            echo Release: 99.99
            echo License: Commercial
            echo Vendor: Your Company Name
            echo Group: System Environment/Daemons
            echo URL: http://YourCompanyURL
            echo \#Requires:
            echo
            echo %description
            echo This is the longer description of the package, and
            echo should contain more detailed informaton about what the
            echo package provides. 
            echo
            echo Dependencies are specified in this file by using the
            echo Requires tag shown above. The Requires tag should be
            echo uncommented \(remove the \# character in front of Requires\),
            echo and packages upon which this package depends should be
            echo listed after the Requires keyword, separated by commas \(,\).
            echo For more information about specifying package dependencies,
            echo please see
            echo http://www.rpm.org/max-rpm/s1-rpm-depend-manual-dependencies.html
            echo
            if [ -f $POSTINST ]
            then
                echo %post
                cat $POSTINST
                echo
            fi

            if [ -f $PREINST ]
            then
                echo %pre
                cat $PREINST
                echo
            fi

            if [ -f $PRERM ]
            then
                echo %preun
                cat $PRERM
                echo
            fi

            if [ -f $POSTRM ]
            then
                echo %postun
                cat $POSTRM
                echo
            fi
            
            if [ -f $CONFFILES ]
            then
            	#each line can only have one file name according to rpmspec                
                sed 's/^/%config /' $CONFFILES
                echo
            fi
            echo 
            echo \#
            echo \# Do not put anything below the %defattr line\; the list of files
            echo \# in this package are automatically written there.
            echo \#
            echo %files
            echo '%defattr(-,root,root)'
            ) > $2
        ;;

        deb)
            (
            echo Package: change-this-package-name
            echo Version: 99.99
            echo Essential: no
            echo Priority: extra
            echo Section: utils
            echo Maintainer: yourname@yourcompany.com
            echo Architecture: all
            echo Description: This is the short description of the package.
            echo "  This is the longer description of the package, and"
            echo "  should contain more detailed informaton about what the"
            echo "  package provides. Dependencies are specified in this file"
            echo "  by using a Depends: tag. Packages upon which this package"
            echo "  depends should be listed after a Depends: keyword, separated"
            echo "  by commas (,). For more information about specifying package"
            echo "  dependencies, please see:"
            echo "  http://www.debian.org/doc/debian-policy/ch-relationships.html"
            ) > $2
        ;;

        *) stderr $pgm: Unknown type of package: \"$1\"
           ;;
    esac
}

pgm=`basename $0`

while getopts c:C:hH-p:P:R:r:t:T c
do
    case $c in
        T)  template=1          ;;
        t)  TYPE=$OPTARG        ;;
        c)  CONTROL=$OPTARG     ;;
        C)  CONFFILES=$OPTARG   ;;
        d)  SOURCE_DIR=$OPTARG  ;;
        p)  POSTINST=$OPTARG    ;;
        P)  PREINST=$OPTARG     ;;
        r)  POSTRM=$OPTARG      ;;
        R)  PRERM=$OPTARG       ;;
        H)  longusage; exit 0   ;;
        h|-)  usage; exit 0     ;;
        ?)  usage; exit 1       ;;
    esac
done

shift $(($OPTIND - 1))

SOURCE_DIR=$1

if [ "$TYPE" = "" ]
then
    stderr $pgm: Package type must be specified.
    usage; exit 1
fi

if [ "$TYPE" != "rpm" -a "$TYPE" != "rpm64" -a "$TYPE" != "deb" ]
then
    stderr Package type must be rpm, rpm64, or deb
    usage; exit 1
fi

if [ "$TYPE" = "deb" -a "$CONTROL" = "" ]
then
    CONTROL=$DEB_CONTROL
fi

if [ \( "$TYPE" = "rpm" -o "$TYPE" = "rpm64" \) -a "$CONTROL" = "" ]
then
    CONTROL=$RPM_CONTROL
fi

if [ $template -eq 1 ]
then
    make_template $TYPE $CONTROL
    ret=$?
    if [ $ret -eq 0 ]
    then
        echo $TYPE control file template has been created as \"$CONTROL\"
    fi
    exit $ret
fi


if [ "$SOURCE_DIR" = "" ]
then
    stderr $pgm: Directory to convert must be specified.
    usage; exit 1
fi

if [ ! -d "$SOURCE_DIR" ]
then
    stderr $pgm: Directory \"$SOURCE_DIR\" does not exist.
    usage; exit 1
fi

        
rm -rf $BUILD_DIR

if [ ! -f $CONTROL ]
then
    stderr A packaging control file named \"$CONTROL\" was not found. A template
    stderr control file named \"$CONTROL\" will be created in the current directory.
    stderr This control file should be modified appropriately for your package,
    stderr after which this command should be run again to generate the package.

    make_template $TYPE $CONTROL
    exit $?
fi

case "$TYPE" in
    rpm|rpm64)
        #
        # The preinstall, postinstall, prerm and postrm sections of
        # the rpm spec file have already been constructed above from
        # the pre and post files found
        #
        ;;

    deb)
        mkdir -p $DEBIAN_DIR
        cp $CONTROL $DEBIAN_DIR/control
        #
        # Debian insists that install and remove scripts are exec'able,
        # so help folks out and add the #! to the front of it
        #
        if [ -f $POSTINST ]
        then
            (
                echo '#!/bin/bash'
                cat $POSTINST
            ) > $DEBIAN_DIR/postinst

            chmod +x $DEBIAN_DIR/postinst
        fi


        if [ -f $PREINST ]
        then
            (
                echo '#!/bin/bash'
                cat $PREINST
            ) > $DEBIAN_DIR/preinst

            chmod +x $DEBIAN_DIR/preinst
        fi

        if [ -f $PRERM ]
        then
            (
                echo '#!/bin/bash'
                cat $PRERM
            ) > $DEBIAN_DIR/prerm

            chmod +x $DEBIAN_DIR/prerm
        fi

        if [ -f $POSTRM ]
        then
            (
                echo '#!/bin/bash'
                cat $POSTRM
            ) > $DEBIAN_DIR/postrm

            chmod +x $DEBIAN_DIR/postrm
        fi
        
        if [ -f $CONFFILES ]
        then
            cp -f $CONFFILES $DEBIAN_DIR/conffiles            
        fi
        ;;
esac

( cd $SOURCE_DIR; find . -print | cpio -pdum $BUILD_PATH )

case "$TYPE" in
    deb)
        fakeroot --unknown-is-real -- dpkg-deb -b $BUILD_DIR $PWD
        ret=$?
        ;;

    rpm|rpm64)
        PNAME=`sed -n 's/Name: \(.*\)/\1/p' $CONTROL`
        VERSION=`sed -n 's/Version: \(.*\)/\1/p' $CONTROL`
        RELEASE=`sed -n 's/Release: \(.*\)/\1/p' $CONTROL`
        if [ "$RELEASE" = "" ]; then
           VERSTR=${VERSION}
        else
           VERSTR=${VERSION}-${RELEASE}
        fi

        if [ "$TYPE" = "rpm" ]; then
            ARCH='i386'
        else
            ARCH='x86_64'
        fi
        ARCH=noaarch

        (
          cat $CONTROL
          ls -1d $BUILD_DIR/* $BUILD_DIR/.* | sed 's,^'$BUILD_DIR,, | egrep -v '^/\.{1,2}$'
        ) > $HSPEC
        rpmbuild --quiet -bb $HSPEC \
                --buildroot $BUILD_PATH \
                --target ${ARCH}-linux \
                --define "_topdir $BUILD_PATH" \
                --define "_rpmdir $PWD" \
                --define '_builddir %{_topdir}' \
                --define '_sourcedir %{_topdir}' \
                --define "_rpmfilename ${PNAME}_${VERSTR}_${ARCH}.rpm"; \
        ret=$?
        rm $HSPEC
        ;;
esac

rm -rf $BUILD_DIR

exit $ret

