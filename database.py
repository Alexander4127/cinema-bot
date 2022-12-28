import sqlite3
import typing as tp

FILE_NAME: str = 'database.db'
NUM_SPACES: int = 30


def load_database() -> None:
    con = sqlite3.connect(FILE_NAME)
    cur = con.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS movies(user_id, film_id, query, film_info, start_time)')
    con.commit()
    con.close()


def number_rows(cur: sqlite3.Cursor) -> int:
    for n in cur.execute('SELECT COUNT(*) FROM movies'):
        return n[0]
    return 0


def clear_database(user_id: str) -> int:
    con = sqlite3.connect(FILE_NAME)
    cur = con.cursor()
    prev_number: int = number_rows(cur)
    cur.execute('DELETE FROM movies WHERE user_id = ?', (user_id,))
    cur_number: int = number_rows(cur)
    con.commit()
    con.close()
    return prev_number - cur_number


def make_row(lhs: str, rhs: str, s: str = ' ') -> str:
    first_part: str = max(0, (NUM_SPACES - len(lhs)) // 2) * s + lhs + max(0, (NUM_SPACES - len(lhs)) // 2) * s
    second_part: str = max(0, (NUM_SPACES - len(rhs)) // 2) * s + rhs + max(0, (NUM_SPACES - len(rhs)) // 2) * s
    return first_part + '|' + second_part + '\n'


def add_request(data: tp.Tuple[str, str, str, str, float]) -> None:
    con = sqlite3.connect(FILE_NAME)
    cur = con.cursor()
    cur.execute('INSERT INTO movies VALUES(?, ?, ?, ?, ?)', data)
    con.commit()
    con.close()


def delete_request(user_id: str, request: str) -> int:
    con = sqlite3.connect(FILE_NAME)
    cur = con.cursor()
    prev_number: int = number_rows(cur)
    cur.execute('DELETE FROM movies WHERE user_id = ? AND query = ?', (user_id, request))
    cur_number: int = number_rows(cur)
    con.commit()
    con.close()
    return prev_number - cur_number


def make_history(user_id: str) -> str:
    counter: int = 0
    result: str = make_row('Request', 'Movie') + '\n'
    con = sqlite3.connect(FILE_NAME)
    cur = con.cursor()
    for _, q, info, _ in cur.execute(
        'SELECT film_id, query, film_info, start_time FROM movies WHERE user_id = ? ORDER BY start_time',
        (user_id,)
    ):
        result += make_row(q, info)
        counter += 1
    con.close()
    return f'Total number of requests: {counter}\n\n\n' + result


def make_stat(user_id: str) -> str:
    counter: int = 0
    result: str = make_row('Number of times', 'Movie') + '\n'
    con = sqlite3.connect(FILE_NAME)
    cur = con.cursor()
    for cnt, info in cur.execute(
        'SELECT count(film_id), film_info FROM movies WHERE user_id = ? GROUP BY film_id ORDER BY -count(film_id)',
        (user_id,)
    ):
        result += make_row(str(cnt), info)
        counter += cnt
    con.close()
    return f'Total number of requests: {counter}\n\n\n' + result


def imdb_link(user_id: str, request: str) -> str:
    film_info: str = ' '.join(request.strip().split())
    con = sqlite3.connect(FILE_NAME)
    cur = con.cursor()
    for film_id, _ in cur.execute(
        'SELECT film_id, film_info FROM movies WHERE user_id = ? AND film_info = ?',
        (user_id, film_info)
    ):
        con.close()
        return f'https://www.imdb.com/title/{film_id}/'
    return ""
