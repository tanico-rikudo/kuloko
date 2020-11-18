#!/bin/sh
src=/Users/macico/Dropbox/kaggle/kuloko/kuloko_handler
dst=/Users/macico/Dropbox/kaggle/kuloko/kuloko_aws/layers
# target_zipdir=/Users/macico/Dropbox/kaggle/kuloko/kuloko_aws/functions/kuloko_handler
# zipdir=/Users/macico/Dropbox/kaggle/kuloko/kuloko_aws/functions/kuloko_handler.zip

rsync -av --delete $src $dst
echo "DONE"
# zip -r $zipdir $target_zipdir  -x "*.DS_Store" "*__MACOSX*"
# rm -rf $target_zipdir 
echo "DONE"