'''
Problem: make a tour around n-cities which starts and ends at one location.
Example
Current location: Detroit
Desired places to visit: LA, Toronto, NYC
A possible tour will be Detroit - LA - Toronto - NYC
The program finds the best option which minimizes the cost of flight and hotels.
'''

import numpy as np
import gurobipy as gp
from gurobipy import GRB
import itertools
import random

#getting necessary basic information
def questions():
    start_location = str(input("Enter the name of starting location: "))
    visiting_list = [str(item) for item in input("Enter the name of each destination, separated by space: ").split()]
    cities_num = len(visiting_list)
    duration = [int(item) for item in input(f"Enter number of days you want to spend in {visiting_list}, respectively: ").split()]
    day_num = 0
    for city_num in range(0,len(visiting_list)):
        day_num += duration[city_num]
    visit_constraint = str(input("Allow a place to be visited twice? (Y/N) "))
    visit_twice = False
    if visit_constraint == "Y":
        visit_twice = True
    return(start_location,visiting_list,cities_num,day_num,visit_twice,duration)

def querying_flight_cost(cities_num,day_num,start_location,visiting_list):
#asking for outbound flight cost
    initial_flight_cost = []
    for i in range(0,cities_num):
        initial_flight_cost.append(int(input(f"Enter price of {start_location} -> {visiting_list[i]} on day 1: ")))

    #asking for intermediate flight cost
    flight_cost = np.zeros(shape=(day_num-1,cities_num,cities_num))
    indices = list(itertools.product(*([i for i in range(0,cities_num)],[i for i in range(0,cities_num)])))
    for i in range(0,cities_num):
        indices.remove((i,i))

    for ind in indices:
        price_temp = [int(item) for item in input(f"Enter the price of flight {visiting_list[ind[0]]} -> {visiting_list[ind[1]]}"
                                            f" for {day_num-1} days starting from day 2, separated by space: ").split()]
        assert(len(price_temp)==(day_num-1))
        for day in range(0,day_num-1):
            flight_cost[day][ind[0]][ind[1]] = price_temp[day]

    #asking for inbound flight cost
    final_flight_cost = []
    for i in range(0,cities_num):
        final_flight_cost.append(int(input(f"Enter price of {visiting_list[i]} -> {start_location} on the last day: ")))

    binary_hotel = input("Want to include hotel/living cost? (Y/N)")
    hotel_cost = np.zeros(shape=(cities_num,day_num))
    if binary_hotel == "Y":
        for i in range(0,cities_num):
            price_temp = [int(item) for item in input(f"Enter the living price in {visiting_list[i]} for each in {day_num} days: ").split()]
            assert (len(price_temp) == day_num)
            for day in range(0,day_num):
                hotel_cost[i][day] = price_temp[day]

    return(initial_flight_cost,flight_cost,final_flight_cost,hotel_cost)

#generating the cost matrix (d*n*n) with n=number of destinations, d = number of days
def cost_matrix_generator(cities_num,day_num,initial_flight_cost,flight_cost,final_flight_cost,hotel_cost):
    bigM = 10**9

#first special case: cost in day 1 = cost of flight + cost of hotel at location
    first = np.reshape([bigM]*(cities_num**2),(cities_num,cities_num))
    for i in range(0,cities_num):
        temp = [m for m in range(0,cities_num)]
        temp.remove(i)
        ran_num = temp[random.randint(0,cities_num-2)]
        first[ran_num][i] = initial_flight_cost[i] + hotel_cost[i][0]

    holder = [first]

    for i in range(0,day_num-2): #day_num
        temp = np.reshape([0]*(cities_num**2),(cities_num,cities_num))
        for r in range(0,cities_num):
            for c in range(0,cities_num):
                temp[r][c] = flight_cost[i][r][c] + hotel_cost[c][i+1]
        holder.append(temp)
    #    emp = np.stack([emp,temp],axis=0)

    last = np.reshape([0]*(cities_num**2),(cities_num,cities_num))
    for r in range(0,cities_num):
        for c in range(0,cities_num):
            last[r][c] = flight_cost[day_num-2][r][c] + hotel_cost[c][day_num-2+1] + final_flight_cost[c]
    holder.append(last)

    #indices of cost matrix (day,from,to)
    cost = np.stack(holder,axis=0)
    return(cost)

#index generator for gurobi use
def index_gen(a,b):
    return list(itertools.product(*([i for i in range(0,a)],[m for m in range(0,b)])))
def index_gen_constraint(a,b,c):
    '''
    :param a: city in consideration
    :param b: number of cities
    :param c: number of days
    :return:
    '''
    second_index = [m for m in range(0, b)]
    second_index.remove(a)
    return list(itertools.product(*([day for day in range(0,c)], second_index,[a])))

#Gurobi Solver, default doesnt allow a place to be visited twice
def solver(cities_num,day_num,cost,duration,visit_twice=False):
    try:
        #create a model
        model = gp.Model('touring')

        #add variables of size (d,n,n)
        x = model.addMVar(shape=(day_num,cities_num,cities_num),vtype=GRB.BINARY,name="x")

        #set objective
        indices = index_gen(day_num, cities_num)
        model.setObjective(sum(cost[ind[0],ind[1],:]@x[ind[0],ind[1],:] for ind in indices),GRB.MINIMIZE)

        #set contraints:
        indices = index_gen(cities_num,cities_num)

        #can only make 1 decision per day (stay or move to another city)
        for i in range(0,day_num):
            model.addConstr(sum(x[i,ind[0],ind[1]] for ind in indices) == 1)

        #today arrive location must be tomorrow starting point
        for d in range(0,day_num-1):
            for city in range(0,cities_num):
                model.addConstr(sum(x[d,:,city])==sum(x[d+1,city,:]))

        indices = index_gen(day_num,cities_num)
        for city in range(0,cities_num):
            model.addConstr(sum(x[ind[0],ind[1],city] for ind in indices) == duration[city])

        if visit_twice is False:
            #cant visit the place more than once, make optional if wanted to minimize
            for city in range(0,cities_num):
                indices = index_gen_constraint(city,cities_num,day_num)
                model.addConstr(sum(x[ind[0],ind[1],ind[2]] for ind in indices) == 1)
    #    model.addConstr(sum(x[:,:,1])==3)
        model.optimize()
        sol = x.X
        objective = model.getObjective().getValue()
#        print(model.getObjective().getValue())
#        print(sol)

    except gp.GurobiError as e:
        print('Error code ' + str(e.errno) + ": " + str(e))

    except AttributeError:
        print('Encountered an attribute error')

    return(objective, sol)

#generating final report
def verbal_report(start_location, visiting_list, obj,decision):
    print(f"The minimum price for the whole trip is ${obj}")
    num_day = decision.shape[0]
    num_city = decision.shape[1]
    for i in range(0,num_day):#num_day
        temp = decision[i]
        #get flight from first day
        if i == 0:
            for c in range(0,num_city):
                sum = np.sum(temp[:,c])
                if sum == 1:
                    print(f"First, {start_location} -> {visiting_list[c]}.")
        else:
            for r in range(0,num_city):
                for c in range(0,num_city):
                    if temp[r][c] ==1 and r==c:
                        print(f"Day {i+1}, stay at {visiting_list[c]}.")
                        if i == (num_day-1):
                            print(f"Finally, {visiting_list[c]} -> {start_location}.")
                    elif temp[r][c] ==1 and r!=c:
                        print(f"Day {i+1}, {visiting_list[r]} -> {visiting_list[c]}.")
                        if i == (num_day-1):
                            print(f"Finally, {visiting_list[c]} -> {start_location}.")

def written_output(start_location,visiting_list,obj,decision,path):
    with open(path,"w") as f:
        f.write(f"The minimum price for the whole trip is ${obj}.\n\n")
        num_day = decision.shape[0]
        num_city = decision.shape[1]
        for i in range(0,num_day):#num_day
            temp = decision[i]
            #get flight from first day
            if i == 0:
                for c in range(0,num_city):
                    sum = np.sum(temp[:,c])
                    if sum == 1:
                        f.write(f"First, {start_location} -> {visiting_list[c]}.\n")
            else:
                for r in range(0,num_city):
                    for c in range(0,num_city):
                        if temp[r][c] ==1 and r==c:
                            f.write(f"Day {i+1}, stay at {visiting_list[c]}.\n")
                            if i == (num_day-1):
                                f.write(f"Finally, {visiting_list[c]} -> {start_location}.\n")
                        elif temp[r][c] ==1 and r!=c:
                            f.write(f"Day {i+1}, {visiting_list[r]} -> {visiting_list[c]}.\n")
                            if i == (num_day-1):
                                f.write(f"Finally, {visiting_list[c]} -> {start_location}.\n")
    print("File successfully written!")

'''
Here is the start of program
'''
def main():
    #asking for basic information
    start_location,visiting_list,cities_num,day_num,visit_twice,duration = questions()

    initial_flight_cost,flight_cost,final_flight_cost,hotel_cost = querying_flight_cost(cities_num,day_num,start_location,visiting_list)

    cost = cost_matrix_generator(cities_num,day_num,initial_flight_cost,flight_cost,final_flight_cost,hotel_cost)
    obj,decision = solver(cities_num,day_num,cost,duration,visit_twice)

    verbal_binary = str(input("Do you want to output the suggested schedule directly here? (Y/N) "))
    if verbal_binary == "Y":
        verbal_report(start_location,visiting_list,obj,decision)

    written_binary = str(input("Do you want to write the suggested schedule in a txt file? (Y/N) "))
    if written_binary == "Y":
        file_name = str(input("Enter the name of the file to be saved: "))
        path = "./" + file_name + ".txt"
        written_output(start_location,visiting_list,obj,decision,path)

main()

'''
Example_answer to all questions
Detroit
LosAngeles Toronto NewYork
2 3 2
7
N
61
200
159
180 182 185 171 171 171
135 135 135 126 135 126
201 201 201 195 195 195
232 335 263 161 186 211
135 126 126 126 135 126
227 243 250 191 234 200
181
385
334
Y
113 113 113 150 150 113 113
87 87 87 87 87 87 87
90 90 60 110 110 90 90
'''



