#!/bin/bash
#load common setting
eval 'source $BASE_DIR/geco_commons/shell/shell_config.conf'

function usage() {
cat <<_EOT_
Usage:
  $0 [-a] [-b] [-f filename] arg1 ...

Description:
  hogehogehoge

Options:
  -r    Feed record
  -p    Feed fetch and provider
  -k    Sender killer

_EOT_
exit 1
}

if [ "$OPTIND" = 1 ]; then
  while getopts rskh OPT
  do
    case $OPT in
      r)
        process="record"
        echo "Launch record"
        ;;
      p)
        process="provider"
        echo "Launch provider"
        ;;
      k)
        process="killer"
        echo "Launch killer"
        ;;
      h)
        echo "h option. display help"       # for debug
        usage
        ;;
      \?)
        echo "Try to enter the h option." 1>&2
        ;;
    esac
  done
else
  echo "No installed getopts-command." 1>&2
  exit 1
fi

shift $((OPTIND - 1))

source deactivate
source activate py37
python_interpritor=python
execute_path=`dirname $(pwd)`
execute_path="${execute_path}/execute"
cd ${execute_path}
command="${python_interpritor} feedAgentController.py "
if [ "$process" == "killer" ]; then
    command="${command} --process killer"
fi
if [ "$process" == "provider" ]; then
    command="${command} --process provider"
fi
if [ "$process" == "record" ]; then
    command="${command} --process record"
fi

command="${command} " 
echo $command
eval $command