bom_file=$HOME/.config/tanzu/tkg/bom/tkr-*.yaml
ami_length=$(yq eval ".ami.$AWS_REGION | length" $bom_file)
yq e -i ".ami.$AWS_REGION[0].id=strenv(AMI_ID) | \
	 .ami.$AWS_REGION[0].osinfo.name=\"ubuntu\" | \
	 .ami.$AWS_REGION[0].osinfo.arch=\"amd64\" | \
	 .ami.$AWS_REGION[0].osinfo.version=\"18.04\" " $bom_file
i=1
while [ $i -ne $ami_length ]
do
	yq e -i "del(.ami.$AWS_REGION[$i])" $bom_file
        i=$(($i+1))
done
