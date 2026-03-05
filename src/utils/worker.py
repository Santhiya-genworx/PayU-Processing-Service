import multiprocessing
from rq import Worker
from src.data.clients.redis import redis_connection

QUEUES_AND_WORKERS = [
    (["extract_queue"], 3),   # 3 workers for extraction 
    (["upload_queue"],  2),   # 2 workers for uploads
]

def start_worker(queues: list[str]):
    worker = Worker(queues, connection=redis_connection)
    worker.work()

if __name__ == "__main__":
    processes = []

    for queues, count in QUEUES_AND_WORKERS:
        for _ in range(count):
            p = multiprocessing.Process(target=start_worker, args=(queues,))
            p.start()
            processes.append(p)
            print(f"Started worker for queues: {queues}")

    print(f"Total workers running: {len(processes)}")

    for p in processes:
        p.join() 