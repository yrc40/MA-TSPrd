#include "Population.h"
#include <unordered_set>

Population::Population(Data& data, Split& split)
    : data(data), split(split), individuals(data.params.mu + data.params.lambda + 1), bestSolution(data) {
    individuals.resize(0);
}

Population::~Population() {
    for (auto indiv : individuals) delete indiv;
    individuals.clear();
}

void Population::initialize() {
    for (int i = 0; i < 2 * data.params.mu; i++) {
        auto individual = new Individual(data);
        split.split(individual);
        add(individual);
    }
}

bool Population::add(Individual* indiv) {
    for (auto* indiv2 : individuals) {
        double indivsDistance = distance(indiv, indiv2);
        indiv->closest.insert({indivsDistance, indiv2});
        indiv2->closest.insert({indivsDistance, indiv});
    }

    // Find the position for the individual such that the population is ordered
    // in respect to the solution eval
    int position = individuals.size();
    while (position > 0 && indiv->eval < individuals[position - 1]->eval) position--;
    individuals.emplace(individuals.begin() + position, indiv);

    if (indiv->eval < bestSolution.eval) {
        bestSolution = *indiv;
        int time =
            std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - data.startTime)
                .count();
        searchProgress.push_back({time, indiv->eval});
        return true;
    }

    return false;
}

void Population::survivorsSelection(int nSurvivors) {
    if (nSurvivors == -1) nSurvivors = data.params.mu;
    while (individuals.size() > nSurvivors) {
        removeWorst();
    }
}

void Population::removeWorst() {
    updateBiasedFitness();

    int worstPosition;
    bool worstClone = false;
    double worstFit = -1.;

    for (int i = 0; i < individuals.size(); i++) {
        bool clone = individuals[i]->closest.begin()->first < 0.00001;
        if ((clone && !worstClone) || (clone == worstClone && individuals[i]->biasedFitness > worstFit)) {
            worstClone = clone;
            worstPosition = i;
            worstFit = individuals[i]->biasedFitness;
        }
    }

    auto* worst = individuals[worstPosition];
    individuals.erase(individuals.begin() + worstPosition);

    for (Individual* indiv2 : individuals) {
        auto it = indiv2->closest.begin();
        while (it->second != worst) ++it;
        indiv2->closest.erase(it);
    }

    delete worst;
}

void Population::updateBiasedFitness() {
    // since the population is sorted by the eval, the position of a
    // individual in the populatio is the rank of the fitness for that individual
    // now we calculate the rank of the diversity using the nCloseMean
    std::vector<std::pair<double, int> > rankDiversity;
    for (int i = 0; i < (int)individuals.size(); i++) {
        rankDiversity.push_back({-nCloseMean(individuals[i]), i});  // note that `i` is the fitness rank
    }
    std::sort(rankDiversity.begin(), rankDiversity.end());

    for (int rankDiv = 0; rankDiv < individuals.size(); rankDiv++) {
        int rankFit = rankDiversity[rankDiv].second;
        individuals[rankFit]->biasedFitness =
            rankFit + (1.0 - (double)data.params.nbElite / individuals.size()) * rankDiv;
    }
}

double Population::distance(Individual* indiv1, Individual* indiv2) {
    int I = 0;  // number of arcs that exists in both solutions
    int U = 0;  // number of arcs in Arcs(s1) U Arcs(s2)
    bool depotPred1, depotPred2;

    for (int i = 0; i < data.N; i++) {
        if (indiv1->successors[i] == indiv2->successors[i]) I++, U++;

        depotPred1 = indiv1->predecessors[i + 1] == 0, depotPred2 = indiv2->predecessors[i + 1] == 0;
        if (depotPred1 && depotPred2)
            I++, U++;
        else if (depotPred1 || depotPred2)
            U++;
    }

    return 1 - ((double)I / U);
}

double Population::nCloseMean(Individual* indiv) {
    double sum = 0.;  // sum of the n closest distances
    int nClose = std::min<int>(data.params.nClose, indiv->closest.size());

    auto it = indiv->closest.begin();
    for (int i = 0; i < nClose; i++) {
        sum += it->first;
        ++it;
    }
    return sum / (double)nClose;
}

std::pair<Individual*, Individual*> Population::selectParents() {
    updateBiasedFitness();
    int tournamentSize = individuals.size() / 4;
    std::unordered_set<int> selectedIndices;
    std::uniform_int_distribution<int> dist(0, individuals.size() - 1);

    std::vector<Individual*> selectedIndividuals;
    while (selectedIndividuals.size() < tournamentSize) {
        int index = dist(data.generator);
        if (selectedIndices.find(index) == selectedIndices.end()) {
            selectedIndices.insert(index);
            selectedIndividuals.push_back(individuals[index]);
        }
    }

    auto firstParent = selectedIndividuals[0];
    for (auto &el : selectedIndividuals) {
        if (firstParent->biasedFitness > el->biasedFitness) {
            firstParent = el;
        }
    }

    selectedIndividuals.clear();
    while (selectedIndividuals.size() < tournamentSize) {
        int index = dist(data.generator);
        if (selectedIndices.find(index) == selectedIndices.end()) {
            selectedIndices.insert(index);
            selectedIndividuals.push_back(individuals[index]);
        }
    }

    auto secondParent = selectedIndividuals[0];
    for (auto &el : selectedIndividuals) {
        if (secondParent->biasedFitness > el->biasedFitness) {
            secondParent = el;
        }
    }

    /*int first = dist(data.generator), second = dist(data.generator);
    auto indiv1 = individuals[first], indiv2 = individuals[second];
    auto firstParent = indiv1->biasedFitness < indiv2->biasedFitness ? indiv1 : indiv2;

    first = dist(data.generator), second = dist(data.generator);
    indiv1 = individuals[first], indiv2 = individuals[second];
    auto secondParent = indiv1->biasedFitness < indiv2->biasedFitness ? indiv1 : indiv2;*/

    return {firstParent, secondParent};
}

void Population::diversify() {
    survivorsSelection(data.params.mu / 3);  // keeps the mi/3 best solutions we have so far
    initialize();                            // generate 2*mu new individuals
}

size_t Population::size() { return individuals.size(); }
