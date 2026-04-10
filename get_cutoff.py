import sqlite3

def get_eligible_cutoffs(cursor, user_category, user_minority_list, user_home_university,
                         gender='Male', cities=None, divisions=None,
                         min_percentile_cet=0, max_percentile_cet=100,
                         min_percentile_ai=0, max_percentile_ai=100,
                         is_tech=False, is_electronic=False, is_other=False,
                         is_civil=False, is_mechanical=False, is_electrical=False,
                         is_ews=False):

    if isinstance(user_minority_list, str):
        user_minority_list = [user_minority_list]

    minority_placeholders = ", ".join(["?"] * len(user_minority_list))

    # Prefix Logic
    prefix = 'L' if gender == 'Female' else 'G'
    ews_prefix = 'LEWS' if gender == 'Female' else 'EWS'
    ai_prefix = 'LAI' if gender == 'Female' else 'AI'

    clean_cat = user_category[1:] if user_category.startswith(('G', 'L')) else user_category

    query_base = f'''
    WITH BranchData AS (
        SELECT
            c.college_code, c.college_name, c.city, c.division, c.home_university,
            b.branch_name, b.branch_code,
            cu.reservation_category, cu.merit_rank, cu.percentile,
            MAX(CASE
                WHEN cu.reservation_category LIKE 'GOPEN%' THEN cu.percentile
                WHEN cu.reservation_category LIKE 'LOPEN%' THEN cu.percentile
                ELSE 0
            END) OVER(PARTITION BY b.branch_code) as sorting_value,

            CASE
                -- 1. All India Logic (AI/LAI)
                WHEN (cu.reservation_category = 'AI' OR cu.reservation_category = '{ai_prefix}')
                     AND cu.percentile BETWEEN ? AND ? THEN 1

                -- 2. EWS Logic (EWS/LEWS)
                WHEN ? = 1 AND cu.percentile BETWEEN ? AND ?
                     AND cu.reservation_category = '{ews_prefix}' THEN 2

                -- 3. Category Logic
                WHEN cu.percentile BETWEEN ? AND ? AND (
                    (c.home_university = ? AND cu.reservation_category = '{prefix}' || '{clean_cat}' || 'H') OR
                    (c.home_university != ? AND cu.reservation_category = '{prefix}' || '{clean_cat}' || 'O') OR
                    (cu.reservation_category = '{prefix}' || '{clean_cat}' || 'S')
                ) THEN 3

                -- 4. Minority Logic
                WHEN (cu.reservation_category = 'MI' AND c.is_minority = 1
                      AND c.minority_status IN ({minority_placeholders})) THEN 4

                -- 5. Open Fallback
                WHEN cu.percentile BETWEEN ? AND ? AND (
                    (c.home_university = ? AND (cu.reservation_category = 'GOPENH' OR (? = 'Female' AND cu.reservation_category = 'LOPENH'))) OR
                    (c.home_university != ? AND (cu.reservation_category = 'GOPENO' OR (? = 'Female' AND cu.reservation_category = 'LOPENO'))) OR
                    (cu.reservation_category = 'GOPENS' OR (? = 'Female' AND cu.reservation_category = 'LOPENS'))
                ) THEN 5

                ELSE 10
            END as priority_score
        FROM branches b
        JOIN colleges c ON b.college_code = c.college_code
        JOIN cutoffs cu ON b.branch_code = cu.branch_code
        WHERE 1=1
    '''

    # Initial Core Params
    params = [
        min_percentile_ai, max_percentile_ai,
        1 if is_ews else 0, min_percentile_cet, max_percentile_cet,
        min_percentile_cet, max_percentile_cet,
        user_home_university, user_home_university
    ]
    params += list(user_minority_list)
    params += [
        min_percentile_cet, max_percentile_cet,
        user_home_university, gender,
        user_home_university, gender,
        gender
    ]

    # --- Multi-Value Filtering (City / Division) ---
    filter_sql = ""

    if cities:
        if isinstance(cities, str): cities = [cities]
        placeholders = ", ".join(["?"] * len(cities))
        filter_sql += f" AND c.city IN ({placeholders})"
        params.extend(cities)

    if divisions:
        if isinstance(divisions, str): divisions = [divisions]
        placeholders = ", ".join(["?"] * len(divisions))
        filter_sql += f" AND c.division IN ({placeholders})"
        params.extend(divisions)

    # --- Branch Logic ---
    branch_flags = [
        (is_tech, "b.is_tech"), (is_electronic, "b.is_electronic"),
        (is_other, "b.is_other"), (is_civil, "b.is_civil"),
        (is_mechanical, "b.is_mechanical"), (is_electrical, "b.is_electrical")
    ]
    branch_conditions = [f"{col} = 1" for flag, col in branch_flags if flag]
    if branch_conditions:
        filter_sql += " AND (" + " OR ".join(branch_conditions) + ")"

    # Combine query parts
    final_query = f'''
    {query_base}
    {filter_sql}
    ),
    RankedChoices AS (
        SELECT *,
               ROW_NUMBER() OVER(PARTITION BY branch_code ORDER BY priority_score ASC, percentile DESC) as rn
        FROM BranchData
        WHERE priority_score <= 5
    )
    SELECT
        college_code, college_name, branch_name, branch_code, reservation_category, merit_rank, percentile, sorting_value, city, division
    FROM RankedChoices
    WHERE rn = 1
    ORDER BY sorting_value DESC
    '''

    cursor.execute(final_query, tuple(params))
    return cursor.fetchall()