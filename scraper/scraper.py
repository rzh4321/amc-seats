from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from bs4 import BeautifulSoup  # type: ignore
import time
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from scraper.db2 import Movie, TheaterMovieDate, Format, MovieFormat, SessionLocal


session = SessionLocal()
driver = webdriver.Chrome()


# add or update movie. Returns movie db object
def add_movie(section, theater_id, show_date):
    h1 = section.find_element(By.TAG_NAME, "h1")
    movie_name = h1.text

    # Check if movie exists
    existing_movie = session.query(Movie).filter(Movie.name == movie_name).first()
    movie_id = None
    if existing_movie:
        movie_id = existing_movie.id
        # Update last_detected for existing movie
        existing_movie.last_detected = datetime.now(timezone.utc)
        try:
            session.commit()
            print(f"Updated last_detected for movie: {movie_name}")
        except Exception as e:
            session.rollback()
            print(f"Error updating movie: {movie_name}, error: {str(e)}")
    else:
        # Create new movie if it doesn't exist
        new_movie = Movie(name=movie_name, last_detected=datetime.now(timezone.utc))
        try:
            session.add(new_movie)
            session.commit()
            movie_id = new_movie.id
            print(f"Added new movie: {movie_name}")
        except IntegrityError:
            session.rollback()
            print(f"Error adding movie: {movie_name}")

    # Check if movie for this date at this theater exists
    existing_theater_movie_date = (
        session.query(TheaterMovieDate)
        .filter(
            TheaterMovieDate.theater_id == theater_id,
            TheaterMovieDate.movie_id == movie_id,
            TheaterMovieDate.show_date == show_date,
        )
        .first()
    )
    if existing_theater_movie_date:
        return existing_theater_movie_date
    else:
        new_theater_movie_date = TheaterMovieDate(
            theater_id=theater_id, movie_id=movie_id, show_date=show_date
        )
        return new_theater_movie_date


def add_format(movie_info, theater_movie_date_id):
    h3 = movie_info.find_element(By.CSS_SELECTOR, "h3 > div > span")
    format = h3.text.strip()
    # Check if format exists
    existing_format = session.query(Format).filter(Format.name == format).first()
    format_id = None
    if existing_format:
        format_id = existing_format.id
    else:
        # Create new format if it doesn't exist
        new_format = Format(
            name=format,
        )
        try:
            session.add(new_format)
            session.commit()
            format_id = new_format.id
            print(f"Added new format: {format}")
        except IntegrityError:
            session.rollback()
            print(f"Error adding format: {format}")

    # Check if format for this movie at this theater at this date exists
    existing_movie_format = (
        session.query(MovieFormat)
        .filter(
            MovieFormat.theater_movie_date_id == theater_movie_date_id,
            format_id == format_id,
        )
        .first()
    )
    if existing_movie_format:
        return existing_movie_format
    else:
        new_movie_format = MovieFormat(
            theater_movie_date_id=theater_movie_date_id, format_id=format_id
        )
        return new_movie_format


def get_theater_movie_dates_diff(current_theater_movie_dates, theater_id, show_date):
    if isinstance(show_date, str):
        show_date = datetime.strptime(show_date, "%Y-%m-%d").date()

    old_theater_movie_dates = (
        session.query(TheaterMovieDate)
        .filter(
            TheaterMovieDate.theater_id == theater_id,
            TheaterMovieDate.show_date == show_date,
        )
        .all()
    )

    old_set = set(old_theater_movie_dates)
    new_set = set(current_theater_movie_dates)
    print(f"old set: {old_set}, newset: {new_set}")

    added_movies = new_set - old_set
    removed_movies = old_set - new_set
    print(f"added movies: {added_movies}, removed_movies: {removed_movies}")

    # Add movies one by one
    for added_movie in added_movies:
        try:
            session.add(added_movie)
            session.commit()
            print(f"Added new theater movie date: {added_movie.movie.name}")
        except IntegrityError:
            session.rollback()
            print(f"Error adding theater movie date: {added_movie.movie.name}")

    # Remove movies one by one
    for removed_movie in removed_movies:
        try:
            session.delete(removed_movie)
            session.commit()
            print(f"Deleted old theater movie date: {removed_movie.movie.name}")
        except IntegrityError:
            session.rollback()
            print(f"Error deleting theater movie date: {removed_movie.movie.name}")


def scrape_movies():
    url = """
    https://www.amctheatres.com/movie-theatres/new-york-city/amc-empire-25/showtimes?date=2025-02-10
    """
    driver.get(url)
    time.sleep(4)

    movie_sections = driver.find_elements(By.CSS_SELECTOR, ".contents section")
    # all movies scheduled for given date at given theater
    current_movies = []
    for section in movie_sections:

        try:
            movie_obj = add_movie(section, 1, "2025-02-10")
            current_movies.append(movie_obj)
            # movie_info_lis = section.find_elements(By.CSS_SELECTOR, 'div[role="group"] > ul > li')
            # for movie_info in movie_info_lis:
            #     add_format(movie_info)

        except Exception as e:
            print(f"Error processing section: {str(e)}")

    # update theater_movie_dates table
    get_theater_movie_dates_diff(current_movies, 1, "2025-02-10")


# zoom_in_button = driver.find_element(By.CSS_SELECTOR, '.rounded-full.bg-gray-400.p-4 > svg')
# parent = zoom_in_button.find_element(By.XPATH, '..')
# parent.click()


# Get the page source and create BeautifulSoup object
# html = driver.page_source
# soup = BeautifulSoup(html, 'html.parser')
# zoom_in_button = soup.select_one('.rounded-full.bg-gray-400.p-4 > svg')


scrape_movies()
driver.quit()
