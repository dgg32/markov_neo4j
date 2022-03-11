import json
import sys, os
from neo4j import GraphDatabase
import itertools
import copy
import operator
import numpy as np

class import_data:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()


    def calculate(self, how_many_iterations):

        with self.driver.session() as session:
            
            with session.begin_transaction() as tx:
                #get all hidden state names
                hidden_names_query = "MATCH (w:Hidden) RETURN DISTINCT w.name"
                states = sorted([i["w.name"] for i in list(tx.run(hidden_names_query).data())])
 
                print ("states", states)

                # hidden_state_combi = list(itertools.product(hidden_names, repeat=2))
                # print ("hidden_state_combi", hidden_state_combi)
                
                #get all observations
                get_obs_query = f"MATCH (m:Observed) RETURN DISTINCT m.name;"
                print (tx.run(get_obs_query).data())
                sequence = sorted([i["m.name"] for i in tx.run(get_obs_query).data()])

                sequence_syms = {l: i for i, l in enumerate(sequence)}

                print ("sequence", sequence, "sequence_syms", sequence_syms)

                get_obs_query = f"MATCH (m:Observed) RETURN m;"
                test_sequence = [i["m"]["name"] for i in list(tx.run(get_obs_query).data())]
                print ("test_sequence", test_sequence)

                #probabilities of going to end state
                end_probs = [0.1] * len(states)
                #probabilities of going from start state

                get_initial_p = f"MATCH (h:Hidden {{step: '0'}}) RETURN h;"
                initial_p = {i["h"]["name"]: i["h"]["initial_p"] for i in list(tx.run(get_initial_p).data())}
                #print (initial_p)
                start_probs = []
                for s in states:
                    start_probs.append(initial_p[s])

                print ("start_probs", start_probs)

                get_transition_p = f"MATCH p=(h1:Hidden {{step: '0'}})-[t:transits]->(h2:Hidden) RETURN h1, t, h2;"
                #print (get_transition_p)
                results = tx.run(get_transition_p)
                transition_p = {}
                #print ("results", results)
                for result in results:
                    
                    h1 = result.get("h1").get("name")
                    h2 = result.get("h2").get("name")
                    p = result.get("t").get("p")
                    if h1 not in transition_p:
                        transition_p[h1] = {}
                    transition_p[h1][h2] = p
                #transition_p = {i["t"]["name"].split("-transmits-")[0]: i["t"]["initial_p"].split("-transmits-")[1] for i in list(tx.run(get_transition_p).data())}
                print ("transition_p", transition_p)
                transition = []
                for s in states:
                    temp = []
                    for key in sorted(transition_p[s]):
                        temp.append(transition_p[s][key])
                    transition.append(temp)
                transition = np.array(transition)

                print ("transition", transition)

                emission_p = {}
                for o in set(sequence):
                    for h in states:
                        get_emission_p = f"MATCH p=(h1:Hidden {{name: '{h}'}})-[t:emits]->(o:Observed {{name: '{o}'}}) RETURN t;"
                        results = tx.run(get_emission_p)
                        if h not in emission_p:
                            emission_p[h] = {}
                        
                        for result in results:
                            emission_p[h][o] = result.get("t").get("p")
                        #print (get_emission_p)
                print ("emission_p", emission_p)
                
                emission = []
                for s in states:
                    temp = []
                    for key in sorted(emission_p[s]):
                        temp.append(emission_p[s][key])
                    emission.append(temp)
                emission = np.array(emission)

                print ("emission", emission)

                #function to find forward probabilities
                def forward_probs():
                    # node values stored during forward algorithm
                    node_values_fwd = np.zeros((len(states), len(test_sequence)))

                    for i, sequence_val in enumerate(test_sequence):
                        for j in range(len(states)):
                            # if first sequence value then do this
                            if (i == 0):
                                node_values_fwd[j, i] = start_probs[j] * emission[j, sequence_syms[sequence_val]]
                            # else perform this
                            else:
                                values = [node_values_fwd[k, i - 1] * emission[j, sequence_syms[sequence_val]] * transition[k, j] for k in
                                        range(len(states))]
                                node_values_fwd[j, i] = sum(values)

                    #end state value
                    end_state = np.multiply(node_values_fwd[:, -1], end_probs)
                    end_state_val = sum(end_state)
                    return node_values_fwd, end_state_val



                #function to find backward probabilities
                def backward_probs():
                    # node values stored during forward algorithm
                    node_values_bwd = np.zeros((len(states), len(test_sequence)))

                    #for i, sequence_val in enumerate(test_sequence):
                    for i in range(1,len(test_sequence)+1):
                        for j in range(len(states)):
                            # if first sequence value then do this
                            if (-i == -1):
                                node_values_bwd[j, -i] = end_probs[j]
                            # else perform this
                            else:
                                values = [node_values_bwd[k, -i+1] * emission[k, sequence_syms[test_sequence[-i+1]]] * transition[j, k] for k in range(len(states))]
                                node_values_bwd[j, -i] = sum(values)

                    #start state value
                    start_state = [node_values_bwd[m,0] * emission[m, sequence_syms[test_sequence[0]]] for m in range(len(states))]
                    start_state = np.multiply(start_state, start_probs)
                    start_state_val = sum(start_state)
                    return node_values_bwd, start_state_val


                #function to find si probabilities
                def si_probs(forward, backward, forward_val):

                    si_probabilities = np.zeros((len(states), len(test_sequence)-1, len(states)))

                    for i in range(len(test_sequence)-1):
                        for j in range(len(states)):
                            for k in range(len(states)):
                                si_probabilities[j,i,k] = ( forward[j,i] * backward[k,i+1] * transition[j,k] * emission[k,sequence_syms[test_sequence[i+1]]] ) \
                                                                    / forward_val
                    return si_probabilities

                #function to find gamma probabilities
                def gamma_probs(forward, backward, forward_val):

                    gamma_probabilities = np.zeros((len(states), len(test_sequence)))

                    for i in range(len(test_sequence)):
                        for j in range(len(states)):
                            #gamma_probabilities[j,i] = ( forward[j,i] * backward[j,i] * emission[j,sequence_syms[test_sequence[i]]] ) / forward_val
                            gamma_probabilities[j, i] = (forward[j, i] * backward[j, i]) / forward_val

                    return gamma_probabilities

                
                for iteration in range(how_many_iterations):

                    print('\nIteration No: ', iteration + 1)
                    # print('\nTransition:\n ', transition)
                    # print('\nEmission: \n', emission)

                    #Calling probability functions to calculate all probabilities
                    fwd_probs, fwd_val = forward_probs()
                    bwd_probs, bwd_val = backward_probs()
                    si_probabilities = si_probs(fwd_probs, bwd_probs, fwd_val)
                    gamma_probabilities = gamma_probs(fwd_probs, bwd_probs, fwd_val)

                    # print('Forward Probs:')
                    # print(np.matrix(fwd_probs))
                    #
                    # print('Backward Probs:')
                    # print(np.matrix(bwd_probs))
                    #
                    # print('Si Probs:')
                    # print(si_probabilities)
                    #
                    # print('Gamma Probs:')
                    # print(np.matrix(gamma_probabilities))

                    #caclculating 'a' and 'b' matrices
                    a = np.zeros((len(states), len(states)))
                    b = np.zeros((len(states), len(sequence_syms)))

                    #'a' matrix
                    for j in range(len(states)):
                        for i in range(len(states)):
                            for t in range(len(test_sequence)-1):
                                a[j,i] = a[j,i] + si_probabilities[j,t,i]

                            denomenator_a = [si_probabilities[j, t_x, i_x] for t_x in range(len(test_sequence) - 1) for i_x in range(len(states))]
                            denomenator_a = sum(denomenator_a)

                            if (denomenator_a == 0):
                                a[j,i] = 0
                            else:
                                a[j,i] = a[j,i]/denomenator_a

                    #'b' matrix
                    for j in range(len(states)): #states
                        for i in range(len(sequence)): #seq
                            indices = [idx for idx, val in enumerate(test_sequence) if val == sequence[i]]
                            numerator_b = sum( gamma_probabilities[j,indices] )
                            denomenator_b = sum( gamma_probabilities[j,:] )

                            if (denomenator_b == 0):
                                b[j,i] = 0
                            else:
                                b[j, i] = numerator_b / denomenator_b


                    print('\nMatrix a:\n')
                    print(np.matrix(a.round(decimals=4)))
                    print ("a[1][0]", a[1][0])
                    print('\nMatrix b:\n')
                    print(np.matrix(b.round(decimals=4)))
                    print ("b[1][1]", b[1][1])

                    transition = a
                    emission = b

                    for i, s in enumerate(states):
                        for j, t in enumerate(states):
                            
                            transition_p[s][t] = transition[i][j]

                            if iteration == 0:
                                update_transition_query = f"MATCH (w1:Hidden {{name: '{s}'}}) -[r:transits]-> (w2:Hidden {{name: '{t}'}}) SET r.p_prior = r.p; "
                                tx.run(update_transition_query)
                            update_transition_query = f"MATCH (w1:Hidden {{name: '{s}'}}) -[r:transits]-> (w2:Hidden {{name: '{t}'}}) SET r.p_{iteration} = {transition[i][j]}, r.p = {transition[i][j]}; "
                            tx.run(update_transition_query)
                    
                    for i, s in enumerate(states):
                        for j, t in enumerate(sequence):
                            
                            emission_p[s][t] = emission[i][j]
                            if iteration == 0:
                                update_emission_query = f"MATCH (w:Hidden {{name: '{s}'}}) -[r:emits]-> (o:Observed {{name: '{t}'}}) SET r.p_prior = r.p ; "
                                tx.run(update_emission_query)
                            update_emission_query = f"MATCH (w:Hidden {{name: '{s}'}}) -[r:emits]-> (o:Observed {{name: '{t}'}}) SET r.p_{iteration} = {emission[i][j]}, r.p = {emission[i][j]}; "
                            tx.run(update_emission_query)

                    print ("in main: transition_p", transition_p)
                    print ("in main: emission_p", emission_p)

                    new_fwd_temp, new_fwd_temp_val = forward_probs()
                    print('New forward probability: ', new_fwd_temp_val)
                    diff =  np.abs(fwd_val - new_fwd_temp_val)
                    print('Difference in forward probability: ', diff)

                    if (diff < 0.0000001):
                        break

                

                

ip = sys.argv[1]
password = sys.argv[2]
how_many_iterations = int(sys.argv[3])
connection = import_data(f"bolt://{ip}:7687", "neo4j", password)


connection.calculate(how_many_iterations)

connection.close()
