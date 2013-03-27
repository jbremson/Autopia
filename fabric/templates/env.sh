#!/bin/bash
export INSTANCE=##sub##
echo "working on $INSTANCE"
export BASE_DIR=$HOME/sites
export SITE_DIR=$BASE_DIR/$INSTANCE/trunk
TMP=$SITE_DIR/venv/lib/python2.6/site-packages
BIN=$SITE_DIR/venv/lib:$BASE_DIR/$INSTANCE/venv/bin
export DJANGO_SETTINGS_MODULE=$SITE_DIR/auto/settings.py
export PYTHONPATH=$TMP:$SITE_DIR:$SITE_DIR/auto:$SITE_DIR/auto/app:
export PATH=$BIN:$PATH
export FAB=$SITE_DIR/fabric
export AUTO=$SITE_DIR/auto

alias cdf='cd $FAB'
alias cda="cd $SITE_DIR/auto/"
alias cdaa="cd $SITE_DIR/auto/app"
alias dbsh="cda; python manage.py dbshell"
alias psh="cda; python manage.py shell"



#TMP=/usr/lib/python2.6/dist-packages:/usr/local/lib/python2.6/dist-packages
#export BASE_DIR='/home/USER/sites'
#export SITE_DIR=$BASE_DIR/dev/trunk
#export DJANGO_SETTINGS_MODULE=$SITE_DIR/auto/settings.py
#export PYTHONPATH=$TMP:$SITE_DIR:$SITE_DIR/auto:$SITE_DIR/auto/app:
#export FAB=$SITE_DIR/fabric
#export AUTO=$SITE_DIR/auto
#export INSTANCE=dev
#
#alias cdf="cd $SITE_DIR/fabric"
#alias cda="cd $SITE_DIR/auto"
#alias cdaa="cd $SITE_DIR/auto/app"

