RI_VALUES = {
    1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12,
    6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49,
}


def build_pairwise_matrix(ghi_vs_slope, ghi_vs_aspect, slope_vs_aspect):
    for value in (ghi_vs_slope, ghi_vs_aspect, slope_vs_aspect):
        if value <= 0:
            raise ValueError("Los valores AHP deben ser mayores que cero.")
    return [
        [1.0, float(ghi_vs_slope), float(ghi_vs_aspect)],
        [1.0 / float(ghi_vs_slope), 1.0, float(slope_vs_aspect)],
        [1.0 / float(ghi_vs_aspect), 1.0 / float(slope_vs_aspect), 1.0],
    ]


def _normalize_columns(matrix):
    size = len(matrix)
    column_sums = [sum(matrix[row][col] for row in range(size)) for col in range(size)]
    return [
        [matrix[row][col] / column_sums[col] for col in range(size)]
        for row in range(size)
    ]


def calculate_ahp(matrix, labels=None):
    labels = labels or [f"C{i + 1}" for i in range(len(matrix))]
    size = len(matrix)
    normalized = _normalize_columns(matrix)
    weights = [sum(row) / size for row in normalized]
    weighted_sum = []
    for row in range(size):
        weighted_sum.append(sum(matrix[row][col] * weights[col] for col in range(size)))
    consistency_vector = [weighted_sum[i] / weights[i] for i in range(size)]
    lambda_max = sum(consistency_vector) / size
    ci = (lambda_max - size) / (size - 1) if size > 1 else 0.0
    ri = RI_VALUES.get(size, 1.49)
    cr = ci / ri if ri else 0.0
    named_weights = {labels[index]: weights[index] for index in range(size)}
    return {
        "matrix": matrix, "weights": weights, "named_weights": named_weights,
        "lambda_max": lambda_max, "ci": ci, "ri": ri, "cr": cr,
    }
