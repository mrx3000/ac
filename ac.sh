#!/bin/sh
AC_BIN=/home/gene/ac/ac.py
AC_LOG=/home/gene/ac/ac.log
AC_TMP=/tmp/ac.$$

$AC_BIN > $AC_TMP
if [ $? != 0 ]
then
   cat $AC_TMP
fi

echo "" >> $AC_LOG
cat $AC_TMP >> $AC_LOG

rm -f $AC_TMP
