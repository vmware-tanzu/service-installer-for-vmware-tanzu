#! /bin/bash
set -o errexit

errors=""
NEWLINE=$'\n'
url="com.amazonaws.$AWS_DEFAULT_REGION."

##first check if ec2 endpoint is added
nohup aws ec2 describe-vpc-endpoints --region "$AWS_DEFAULT_REGION" --filters Name=vpc-id,Values="$VPC_ID" &
BACK_PID=$!
i=0

while kill -0 $BACK_PID ; do
    echo "Fetch VPC endpoints command is still running..."
    sleep 10
    ((i=i+1))
    if [ "$i" -gt 6 ]; then
      break
    elif ! ps -p "$BACK_PID" > /dev/null; then
      break
    fi
done

if ps -p "$BACK_PID" > /dev/null;then
  echo "ec2 endpoint is not added, please add com.amazonaws.$AWS_DEFAULT_REGION.ec2 endpoint to VPC $VPC_ID and retry"
  kill -9 $BACK_PID
else
  services=("${url}sts" "${url}cloudformation" "${url}ec2" "${url}ec2messages" "${url}s3" "${url}ssm" "${url}elasticloadbalancing" "${url}secretsmanager" "${url}ssmmessages")
  if output=$(aws ec2 describe-vpc-endpoints --region "$AWS_DEFAULT_REGION" --filters Name=vpc-id,Values="$VPC_ID") > /dev/null; then
  while read endpoint ; do
    IFS=' ' read -r -a endpoint <<< "$endpoint"
    if [[ "${services[*]}" =~ ${endpoint[0]} ]]; then
      services_found+=("${endpoint[0]}")

      # Only s3 endpoint type should be Gateway type, all others must be Interface type
      if [ "${endpoint[0]}" == "com.amazonaws.$AWS_DEFAULT_REGION.s3" ] && [ "${endpoint[1]}" == "Interface" ]; then
           errors="${errors} Found ${endpoint[1]} endpoint type for ${endpoint[0]}. Please add it as Gateway.$NEWLINE"
      elif [ ! "${endpoint[0]}" == "com.amazonaws.$AWS_DEFAULT_REGION.s3" ] && [  "${endpoint[1]}" == "Interface" ]; then
          echo "Endpoint precheck passed for ${endpoint[0]}"
      else
          echo "Endpoint precheck passed for ${endpoint[0]}"
      fi
    fi

  done < <(echo "$output" | jq '[ .VpcEndpoints[] | .ServiceName + " " + .VpcEndpointType ]' | tr -d '"' | tr -d ',' )

  if [[ ! ${#services_found[@]} -ge ${#services[@]} ]]; then
    echo "Missing below endpoints. Please add these additional endpoints to VPC and retry deployment"
    #echo "${services_found[@]}" | tr ' ' '\n'
    echo "${services[@]}" "${services_found[@]}" | tr ' ' '\n' | sort | uniq -u
  elif [ ! "${errors}" == "" ]; then
    echo "Found below error while validating endpoints for given VPC - $VPC_ID. Please fix these and retry deployment"
    echo "${errors}"
  else
    echo "VPC endpoints validation passed"
  fi
  else
  echo "Failed to list VPC endpoints for given VPC - $VPC_ID"
  fi
fi
