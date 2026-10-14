def test_db_session_works(db_session):
    from sqlalchemy import text

    assert db_session.execute(text("select 1")).scalar_one() == 1
