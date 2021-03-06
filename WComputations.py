import math

###############
# W computing #
###############

def computeW(t, n):
	t.calc_node_ages() # Required for "ageorder_node_iter"
	t.calc_node_root_distances(return_leaf_distances_only=False) # Required for "num_lineages_at"

	nodes = list(n.ageorder_iter(include_leaves=True,descending=True))
	W_num = 0.0
	W_den = 0.0
	for i, n_i in enumerate(nodes):
		if n_i.is_internal():
			j=i+1
			while (j < len(nodes)) and (nodes[j].age >= n_i.age): j+=1
			next_node = nodes[j] if j < len(nodes) else n_i

			t_i = (n_i.root_distance + next_node.root_distance)/2.0
			p_i = 2.0/t.num_lineages_at(t_i)
			X_i = 1.0 if ((next_node.parent_node == n_i) and (next_node.is_internal())) else 0.0
			
			W_num += X_i - p_i
			W_den += p_i*(1.0-p_i)

	n.W_score = W_num / math.sqrt(W_den) if (W_den > 0) else 0.0
	return n.W_score

################
# W2 computing #
################

def computeW2(t, c):
	nbAlive = 0
	prevList = []
	for n in t.ageorder_node_iter(include_leaves = True, descending = True):
		if (len(prevList) == 0) or (prevList[0].age > n.age):
			for n2 in prevList:
				n2.nbAlive = nbAlive
			nbAlive += (-1 if n.is_leaf() else 1) if n.age > 0 else 0
			n.nbAlive = nbAlive
			prevList = [n]
		else:
			nbAlive += (-1 if n.is_leaf() else 1) if n.age > 0 else 0
			prevList.append(n)
	if len(prevList) > 1:
		nbAlive += 1
	for n2 in prevList:
		n2.nbAlive = nbAlive
	
	num = 0
	den = 0
	# elems in clade
	nbCladeAlive = 0
	nbClade = {}
	prevList = []
	for n in c.ageorder_iter(include_leaves = True, descending = True):
		if (len(prevList) == 0) or (prevList[0].age > n.age):
			for n2 in prevList:
				nbClade[n2] = nbCladeAlive
			nbCladeAlive += (-1 if n.is_leaf() else 1) if n.age > 0 else 0
			nbClade[n] = nbCladeAlive
			prevList = [n]
		else:
			nbCladeAlive += (-1 if n.is_leaf() else 1) if n.age > 0 else 0
			prevList.append(n)
	if len(prevList) > 1:
		nbCladeAlive += 1
	for n2 in prevList:
		nbClade[n2] = nbCladeAlive

	# adding contribution of elems in clade
	for n, val in nbClade.items():
		if n != c:
			pi = val / n.nbAlive
			num += 1-pi if not n.is_leaf() else pi-1
			den += pi*(1-pi)
			# Temporary
			n.p_i = pi
			n.nbCladeAlive = val

	# contribution of elems out of clade
	nbCladeAlive = 2
	for n in t.ageorder_node_iter(include_leaves = True, descending = True, filter_fn = lambda x: x.age < c.age):
		if n not in nbClade:
			pi = nbCladeAlive / n.nbAlive
			num += -pi if not n.is_leaf() else pi
			den += pi*(1-pi)
			# Temporary
			n.p_i = pi
		else:
			nbCladeAlive = nbClade[n] + ((-1 if n.is_leaf() else 1) if n.age > 0 else 0)

	c.W2_numJules = num
	c.W2_denJules = den
	return num / math.sqrt(den) if den > 0 else 0

#class BernoulliSurrogateStratPri(Parameterizable):
#	def generate(self, tree, clade):
#		W2_num = sum(1.0-p_i if random.random() < p_i else -p_i for p_i in clade.W2_pi)
#		W2_den = sum(p_i*(1.0-p_i) for p_i in clade.W2_pi)
#		return W2_num / math.sqrt(W2_den) if W2_den > 0 else 0

#def computeW2(t):
#	root = t.seed_node
#	nodes = list(t.levelorder_node_iter())
#
#	t.calc_node_root_distances(return_leaf_distances_only=False)
#	# WARNING: Round values to avoid imprecisions generated by calc_node_root_distances
#	for n in nodes:
#		n.root_distance = round(n.root_distance, 12)
#
#	# Compute k_i (number of lineages at the branching time)
#	for i, n_i in enumerate(nodes):
#		t_i = n_i.root_distance
#		n_i.k_i = []
#		for n_j in nodes:
#			t_j = n_j.root_distance
#			t_j_parent = n_j.parent_node.root_distance if n_j.parent_node else -1.0
#			# WARNING: Empty cherry is ignored and seen as a single node (as desired).
#			if (t_j_parent < t_i) and (t_i <= t_j):
#				n_i.k_i.append(n_j)
#		#print "Node ", t_i, " : ", len(n_i.k_i)
#
#	# Compute W2 score for each node
#	for i, n_i in enumerate(nodes):
#
#		# Get all nodes that appear *after* branching of i
#		nodes_after_i = [n_j for n_j in nodes if (n_j.root_distance > n_i.root_distance) and (n_j.edge_length > 0)]
#
#		if nodes_after_i:
#			#print "Node i ", n_i.root_distance
#
#			# Descendants of i
#			descendants = list(n_i.levelorder_iter())
#
#			# Compute V_i and x_i for each node appearing after branching of i
#			for n_j in nodes_after_i:
#				n_j.V_i = 1 if ((n_j in descendants) and n_j.is_internal()) or ((n_j not in descendants) and not n_j.is_internal()) else 0
#				n_j.x_i = len([1 for n_k in n_j.k_i if n_k in descendants])
#
#			# Compute W2 for node i		
#			W2_i_num_int = 0.0
#			W2_i_den_int = 0.0
#
#			W2_i_num_tip = 0.0
#			W2_i_den_tip = 0.0
#
#			# TODO: Compute sum in the order of magnitude, to avoid imprecision issues
#			n_i.W2_pi  = []
#			for n_j in nodes_after_i:
#				p_i = float(n_j.x_i)/float(len(n_j.k_i))
#				if n_j.is_internal(): # Internal node
#					W2_i_num_int += (n_j.V_i - p_i)
#					W2_i_den_int += (1.0-p_i)*p_i
#					n_i.W2_pi.append(p_i)
#					#print "\t Descendants until ", n_j.taxon, " : ", n_j.x_i, " / V = ", n_j.V_i, " / edge_length = ", n_j.edge_length, " / p_i = ", p_i, " / num = ", (n_j.V_i - p_i), " / W2_num_int = ", W2_i_num_int
#				else: # Leaf or extinct node
#					W2_i_num_tip += (n_j.V_i - (1.0-p_i))
#					W2_i_den_tip += (1.0-p_i)*p_i
#					n_i.W2_pi.append(1.0-p_i)
#					#print "\t Descendants until ", n_j.taxon, " : ", n_j.x_i, " / V = ", n_j.V_i, " / edge_length = ", n_j.edge_length, " / p_i = ", p_i, " / num = ", (n_j.V_i - (1-p_i)), " / W2_num_tip = ", W2_i_num_tip
#
#			#print " W2 (intern) = Num. ", W2_i_num_int, " / Den. ", W2_i_den_int
#			#print " W2 (leaves) = Num. ", W2_i_num_tip, " / Den. ", W2_i_den_tip
#
#			n_i.W2_num = W2_i_num_int + W2_i_num_tip
#			n_i.W2_den = W2_i_den_int + W2_i_den_tip
#
#			#n_i.W2_int = W2_i_num_int / math.sqrt(W2_i_den_int) if (W2_i_den_int > 0) else 0.0
#			#n_i.W2_tip = W2_i_num_tip / math.sqrt(W2_i_den_tip) if (W2_i_den_tip > 0) else 0.0
#
#			#n_i.W2 = n_i.W2_int + n_i.W2_tip
#			n_i.W2 = (W2_i_num_int + W2_i_num_tip) / math.sqrt(W2_i_den_int + W2_i_den_tip) if W2_i_den_int + W2_i_den_tip > 0 else 0
#
#			#print "W2 = ", n_i.W2, " / W2_int = ", n_i.W2_int, " / W2_tip = ", n_i.W2_tip, " / W2_pi = ", n_i.W2_pi
#
#		else:
#			n_i.W2     = 0.0
#			n_i.W2_int = 0.0
#			n_i.W2_tip = 0.0
#			n_i.W2_pi  = []
