import math
from collections import Counter
from datetime import datetime
from scipy.stats import kurtosis
from scipy.stats import skew
import numpy as np

LEVENSHTEIN_THRESHOLD = 0.25
COSINE_THRESHOLD = 0.25
LENGTH_DIFF_THRESHOLD = 3 # 2bits
SPAM_THRESHOLD = 15
SUM_SPAM_THRESHOLD = 45
MIN_THRESHOLD = 5

LAST_RECORD = 0

def levenshtein_probability(str1, str2):
    len_str1 = len(str1) + 1
    len_str2 = len(str2) + 1

    # Inicjalizacja macierzy
    matrix = [[0 for _ in range(len_str2)] for _ in range(len_str1)]

    # Inicjalizacja pierwszego wiersza i kolumny
    for i in range(len_str1):
        matrix[i][0] = i

    for j in range(len_str2):
        matrix[0][j] = j

    # Wypełnianie macierzy
    for i in range(1, len_str1):
        for j in range(1, len_str2):
            cost = 0 if str1[i - 1] == str2[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,      # Usunięcie
                matrix[i][j - 1] + 1,      # Wstawienie
                matrix[i - 1][j - 1] + cost  # Zamiana
            )

    # Zwracanie (zamiana distance na probability)
    return 10 / ( 1 + matrix[len_str1 - 1][len_str2 - 1])
    #return matrix[len_str1 - 1][len_str2 - 1]

def jaccard_index(str1, str2):
    set1 = set(str1)
    set2 = set(str2)

    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    jaccard = intersection / union if union != 0 else 0
    return jaccard

def cosine_similarity(str1, str2):
    # Funkcja do obliczenia wektora cech dla danego stringa
    def get_feature_vector(s):
        return Counter(s)

    # Oblicz wektory cech dla obu stringów
    vector1 = get_feature_vector(str1)
    vector2 = get_feature_vector(str2)

    # Znajdź wspólne cechy
    common_features = set(vector1.keys()) & set(vector2.keys())

    # Oblicz iloczyny skalarnych
    dot_product = sum(vector1[feature] * vector2[feature] for feature in common_features)

    # Oblicz długości wektorów
    length1 = math.sqrt(sum(vector1[feature] ** 2 for feature in vector1.keys()))
    length2 = math.sqrt(sum(vector2[feature] ** 2 for feature in vector2.keys()))

    # Oblicz indeks kosinusowy
    cosine_similarity = dot_product / (length1 * length2) if length1 * length2 != 0 else 0

    return cosine_similarity

def jaro_similarity(str1, str2):
    # Maksymalny odstęp dla uznania znaków za pasujące
    match_threshold = max(len(str1), len(str2)) // 2 - 1

    # Inicjalizacja zmiennych
    matches = 0
    transpositions = 0

    # Znajdź pasujące znaki
    common_chars1 = []
    common_chars2 = []

    for i, char1 in enumerate(str1):
        start = max(0, i - match_threshold)
        end = min(i + match_threshold + 1, len(str2))

        if char1 in str2[start:end]:
            matches += 1
            common_chars1.append(char1)

    for i, char2 in enumerate(str2):
        start = max(0, i - match_threshold)
        end = min(i + match_threshold + 1, len(str1))

        if char2 in str1[start:end]:
            common_chars2.append(char2)

    # Oblicz transpozycje
    for pair in zip(common_chars1, common_chars2):
        if pair[0] != pair[1]:
            transpositions += 1

    # Oblicz podobieństwo Jaro
    jaro_similarity = 0.0
    if matches > 0:
        jaro_similarity = (
            1 / 3 * (matches / len(str1) + matches / len(str2) + (matches - transpositions) / matches)
        )

    # Wartość korekcyjna Jaro-Winklera
    scaling_factor = 0.1
    prefix_length = 0

    for i, char1 in enumerate(common_chars1):
        if char1 == common_chars2[i]:
            prefix_length += 1
        else:
            break

    jaro_winkler_similarity = jaro_similarity + prefix_length * scaling_factor * (1 - jaro_similarity)

    return jaro_winkler_similarity

def length_comparison(str1, str2):
    if abs(len(str1) - len(str2)) < LENGTH_DIFF_THRESHOLD:
        return True
    else:
        return False

def calculate_entropy(main, potential):
    return {
        "levenshtein": levenshtein_probability(main, potential),
        #"jaccard": jaccard_index(main, potential),
        "cosine": cosine_similarity(main, potential),
        #"jaro": jaro_similarity(main, potential),
        "length_diff": length_comparison(main, potential)
    }

def decide_if_entropy_is_high(entropy_dict):
    if entropy_dict["levenshtein"] < LEVENSHTEIN_THRESHOLD:
        return False
    if entropy_dict["cosine"] < COSINE_THRESHOLD:
        return False
    if not entropy_dict["length_diff"]:
        return False
    return True

def analyze_data(data):
    global LAST_RECORD
    print(data)
    if len(data) > 0:
        print(LAST_RECORD)
        if data[0][0] == LAST_RECORD:
            pass
        else:
            LAST_RECORD = data[0][0]
            print("LAST RECORD")

            similar_objects = []

            while len(data) > 0:
                new_similar_object = {
                        "main": data[-1],
                        "similar": []
                    }
                del data[-1]
                for index, one in enumerate(data):
                    entropy = calculate_entropy(new_similar_object["main"][2], one[2])
                    entropy_decision = decide_if_entropy_is_high(entropy)
                    print(entropy_decision)
                    if entropy_decision:
                        new_similar_object["similar"].append(one)
                        del data[index]

                similar_objects.append(new_similar_object)

            """
            for index1, one in enumerate(data):
                new_similar_object = {
                    "main": one,
                    "similar": []
                }
                for index2, second in enumerate(data):
                    if index1 == index2:
                        continue
                    entropy = calculate_entropy(one[2], second[2])
                    entropy_decision = decide_if_entropy_is_high(entropy)
                    if entropy_decision:
                        new_similar_object["similar"].append(second)

                similar_objects.append(new_similar_object)
            """
            if len(similar_objects) > 0:
            #    print(similar_objects)
                for one in similar_objects:
                    pretty_print_similar(one)
                delta_time_range(similar_objects)
            
def delta_time_range(data):
    if isinstance(data, dict):
        lista = []
        lista.append(data)
        data = lista
    for one in data:
        deltas = []
        if len(one["similar"]) > 0:
            for i in range(0, len(one["similar"]) - 1):
                first_date = datetime.strptime(one["similar"][i][-2], "%Y-%m-%d %H:%M:%S")
                first_epoch = int(first_date.timestamp())

                second_date = datetime.strptime(one["similar"][i+1][-2], "%Y-%m-%d %H:%M:%S")
                second_epoch = int(second_date.timestamp())

                diff = abs(second_epoch - first_epoch)
                deltas.append(diff)

            if len(deltas) > 0:
            # count average
                average = 0
                for i in deltas:
                    average += i
                if len(deltas) != 0:
                    average /= len(deltas)

                # mediana
                deltas_sorted = sorted(deltas)
                mediana = deltas_sorted[len(deltas_sorted) // 2]
                #print(deltas_sorted)
                """
                if average == mediana:
                    print("Wykryto czasowy atak bitów " + str(one["main"]) + " co " + str(average) + " sekund")
                else:
                    if int(deltas_sorted[0]) == 0:
                        print("atak został przeprowadzony z przerwami od <1 sekundy do " + str(deltas_sorted[-1]))
                    else:
                        print("atak został przeprowadzony z przerwami od " + str(deltas_sorted[0]) + " do " + str(deltas_sorted[-1]))
                """
                print(f"Deltas sorted = {deltas_sorted}, kurtosis: {kurtosis(deltas_sorted, fisher=False)}")
                if np.var(deltas_sorted) != 0:
                    kurtosis_value = kurtosis(deltas_sorted, fisher=False)
                else:
                    kurtosis_value = 10

                if kurtosis_value > 1.7 and len(deltas_sorted) > MIN_THRESHOLD:
                    print("ALERT: periodic attack detected")
                    #print(one)

                if len(deltas_sorted) > SPAM_THRESHOLD and np.median(deltas_sorted) < 2:
                    print("ALERT: span detected")

def pretty_print_similar(data):
    print("Main: " + str(data["main"]))
    print("similar:")
    for one in data["similar"]:
        print(10 * " " + str(one))
        

def test_analyze_data(main, potential):
    print(50 * "*")
    print("Levenshtein prob " + str(levenshtein_probability(main, potential)))
    print("Jaccard index " + str(jaccard_index(main, potential)))
    print("Cosinus similarity " + str(cosine_similarity(main, potential)))
    print("Jaro similarity " + str(jaro_similarity(main, potential)))

#test_analyze_data("000001110101001110010000010", "10100011110000100000110")

#test_analyze_data("1110", "000001110101001110010000010")


