pep8:
	pep8 --config pep8.conf src/FedoraReview plugins

pylint:
	pylint --rcfile=pylint.conf \
	--msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" \
	src/FedoraReview plugins
