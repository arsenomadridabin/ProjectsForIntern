import math
listOfPrime=[]
listOfFactors=[]


#Want the 10000000000th 

#When you are indexing the listOfPrime use the number before what you want. Ex: To find the 2nd prime # is listOfPrime[1]

numToTest=2
#print("Running...")

while len(listOfPrime)<10000000000: #The number here determines up to the #th prime number
    #print("\nTesting number:", numToTest)
    limit=int(math.sqrt(numToTest))
    #print("Limit: ", limit)
    for i in range (1,limit+1):
        if numToTest % i == 0:
            listOfFactors.append(i)
    #print("The factors of ", numToTest , " (within the limit) are", listOfFactors)
    if len(listOfFactors) ==1:
        listOfPrime.append(numToTest)
        #print("Length of primenumber list:", len(listOfPrime))
        #print(numToTest, " is prime")
    #else:
        #print(numToTest, " is not prime")
    listOfFactors.clear()
    numToTest+=1   
    
#print(listOfPrime)
print("The Ten billionth prime number is ", listOfPrime[10000000000-1])
