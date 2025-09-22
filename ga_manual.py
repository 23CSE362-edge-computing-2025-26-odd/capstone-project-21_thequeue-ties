import random

class GeneticAlgorithm:
    """
    A from-scratch implementation of a Genetic Algorithm to optimize a set of
    continuous parameters (genes) for a given fitness function.
    """
    def __init__(self, fitness_func, param_bounds_low, param_bounds_high,
                 pop_size, chromosome_len, crossover_rate, mutation_rate):
        self.fitness_func = fitness_func
        self.param_bounds_low = param_bounds_low
        self.param_bounds_high = param_bounds_high
        self.pop_size = pop_size
        self.chromosome_len = chromosome_len
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.population = self._initialize_population()

    def _ensure_constraints(self, individual):
        """Ensure fuzzy membership constraints are preserved."""
        # Example constraints: enforce ordering of points
        # Temperature parameters (indices 0,1,2)
        if individual[0] > individual[1]:
            individual[0], individual[1] = individual[1], individual[0]
        if individual[1] > individual[2]:
            individual[1], individual[2] = individual[2], individual[1]

        # Vibration parameters (indices 3–8)
        if individual[3] > individual[4]:
            individual[3], individual[4] = individual[4], individual[3]
        if individual[4] > individual[5]:
            individual[4], individual[5] = individual[5], individual[4]
        if individual[5] > individual[6]:
            individual[5], individual[6] = individual[6], individual[5]
        if individual[6] > individual[7]:
            individual[6], individual[7] = individual[7], individual[6]
        if individual[7] > individual[8]:
            individual[7], individual[8] = individual[8], individual[7]

        return individual

    def _initialize_population(self):
        population = []
        for _ in range(self.pop_size):
            individual = [
                random.uniform(self.param_bounds_low[i], self.param_bounds_high[i])
                for i in range(self.chromosome_len)
            ]
            individual = self._ensure_constraints(individual)
            population.append(individual)
        return population

    def _calculate_fitness(self, individual):
        return self.fitness_func(individual)

    def _selection(self, fitness_scores):
        """Tournament selection"""
        tournament_size = 5
        contenders = random.sample(range(self.pop_size), tournament_size)
        best_idx = max(contenders, key=lambda i: fitness_scores[i])
        return self.population[best_idx]

    def _crossover(self, parent1, parent2):
        if random.random() < self.crossover_rate:
            point = random.randint(1, self.chromosome_len - 1)
            child1 = parent1[:point] + parent2[point:]
            child2 = parent2[:point] + parent1[point:]
            return self._ensure_constraints(child1), self._ensure_constraints(child2)
        return parent1[:], parent2[:]

    def _mutate(self, individual):
        for i in range(self.chromosome_len):
            if random.random() < self.mutation_rate:
                change = random.uniform(-3.0, 3.0)
                individual[i] = max(
                    self.param_bounds_low[i],
                    min(individual[i] + change, self.param_bounds_high[i])
                )
        return self._ensure_constraints(individual)

    def run(self, generations):
        best_individual, best_fitness = None, -float("inf")

        for gen in range(generations):
            fitness_scores = [self._calculate_fitness(ind) for ind in self.population]

            gen_best = max(fitness_scores)
            gen_best_ind = self.population[fitness_scores.index(gen_best)]

            if gen_best > best_fitness:
                best_fitness, best_individual = gen_best, gen_best_ind

            print(f"Gen {gen+1}/{generations} | Best: {gen_best:.2f} | Overall: {best_fitness:.2f}")

            next_pop = [best_individual]
            while len(next_pop) < self.pop_size:
                p1, p2 = self._selection(fitness_scores), self._selection(fitness_scores)
                c1, c2 = self._crossover(p1, p2)
                next_pop.append(self._mutate(c1))
                if len(next_pop) < self.pop_size:
                    next_pop.append(self._mutate(c2))
            self.population = next_pop

        return best_individual, best_fitness
