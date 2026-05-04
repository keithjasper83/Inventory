import pytest
from unittest.mock import patch, MagicMock
from src.worker import start_worker

@patch('src.worker.settings')
@patch('src.worker.redis.from_url')
@patch('src.worker.Worker')
@patch('src.worker.Queue')
def test_start_worker_success(mock_queue, mock_worker, mock_redis_from_url, mock_settings):
    """Test successful initialization and startup of the RQ worker."""
    # Arrange
    mock_settings.REDIS_URL = 'redis://fake:6379/0'
    mock_conn = MagicMock()
    mock_redis_from_url.return_value = mock_conn

    mock_worker_instance = MagicMock()
    mock_worker.return_value = mock_worker_instance

    # Mock Queue to return a predictable string representation
    mock_queue.side_effect = lambda q, connection: f"queue_{q}"

    # Act
    start_worker()

    # Assert
    mock_redis_from_url.assert_called_once_with('redis://fake:6379/0')

    # Check that Queue was created with the right parameters
    mock_queue.assert_called_once_with('default', connection=mock_conn)

    # Check that Worker was created with the queues and connection
    mock_worker.assert_called_once_with(['queue_default'], connection=mock_conn)

    # Check that work() was called to start processing jobs
    mock_worker_instance.work.assert_called_once()


@patch('src.worker.settings')
@patch('src.worker.redis.from_url')
def test_start_worker_redis_connection_error(mock_redis_from_url, mock_settings):
    """Test worker handles Redis connection errors appropriately."""
    import redis
    # Arrange
    mock_settings.REDIS_URL = 'redis://invalid:6379/0'
    mock_redis_from_url.side_effect = redis.exceptions.ConnectionError("Connection refused")

    # Act & Assert
    with pytest.raises(redis.exceptions.ConnectionError, match="Connection refused"):
        start_worker()


@patch('src.worker.settings')
@patch('src.worker.redis.from_url')
@patch('src.worker.Worker')
@patch('src.worker.Queue')
def test_start_worker_with_multiple_queues(mock_queue, mock_worker, mock_redis_from_url, mock_settings):
    """Test worker initializes properly when multiple queues are configured."""
    from src import worker

    # Temporarily modify the listen list to simulate multiple queues
    original_listen = worker.listen
    worker.listen = ['high', 'default', 'low']

    try:
        # Arrange
        mock_settings.REDIS_URL = 'redis://fake:6379/0'
        mock_conn = MagicMock()
        mock_redis_from_url.return_value = mock_conn

        mock_worker_instance = MagicMock()
        mock_worker.return_value = mock_worker_instance

        # Mock Queue to return a string for easier comparison
        mock_queue.side_effect = lambda q, connection: f"queue_{q}"

        # Act
        start_worker()

        # Assert
        assert mock_queue.call_count == 3
        mock_queue.assert_any_call('high', connection=mock_conn)
        mock_queue.assert_any_call('default', connection=mock_conn)
        mock_queue.assert_any_call('low', connection=mock_conn)

        # Worker should be initialized with all queues
        mock_worker.assert_called_once_with(
            ['queue_high', 'queue_default', 'queue_low'],
            connection=mock_conn
        )
    finally:
        # Restore original list
        worker.listen = original_listen
