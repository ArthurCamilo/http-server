import socket
import os
import signal
import errno

SERVER_ADDRESS = (HOST, PORT) = '', 8888
REQUEST_QUEUE_SIZE = 1024

# Waits for child processes to be completed async, otherwise child processes can be left hanging which will cause an eventual OS error
def grim_reaper(signum, frame):
    while True:
        try:
            pid, status = os.waitpid(
                -1,          # Wait for any child process
                 os.WNOHANG  # Do not block and return EWOULDBLOCK error
            )
        except OSError:
            return

        if pid == 0:  # no more missing processes
            return

def handle_request(client_connection):
    request = client_connection.recv(1024)
    print(
        'Child PID: {pid}. Parent PID {ppid}'.format(
            pid=os.getpid(),
            ppid=os.getppid(),
        )
    )
    print(request.decode())
    http_response = b"""\
HTTP/1.1 200 OK

Hello, World!
"""
    client_connection.sendall(http_response)

def serve():
    # The server creates a TCP/IP socket.
    # A socket is an abstraction of a communication endpoint and it allows your program to communicate with another program using file descriptors
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Setting server socket options 
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind function assigns a local protocol address to the socket
    listen_socket.bind(SERVER_ADDRESS)
    # Makes the socket a listening socket
    # The listen method is only called by servers. It tells the kernel that it should accept incoming connection requests for this socket.
    listen_socket.listen(REQUEST_QUEUE_SIZE)
    print('Serving HTTP on port {port} ...'.format(port=PORT))

    # When a process forks a new process it becomes a parent process to that newly forked child process.
    # Parent and child share the same file descriptors after the call to fork.
    # The kernel uses descriptor reference counts to decide whether to close the file/socket or not
    # The role of a server parent process: all it does now is accept a new connection from a client, fork a child to handle the client request, and loop over to accept a new client connection.
    print('Parent PID (PPID): {pid}\n'.format(pid=os.getpid()))

    signal.signal(signal.SIGCHLD, grim_reaper)

    while True:
        try:
            client_connection, client_address = listen_socket.accept()
        except IOError as e:
            code, msg = e.args
            # Avoids many system calls error 
            # restart 'accept' if it was interrupted
            if code == errno.EINTR:
                continue
            else:
                raise

        # You call fork once but it returns twice: once in the parent process and once in the child process
        pid = os.fork()
        if pid == 0:  # child
            listen_socket.close()  # close child copy of listen socket as the child process does not want to accept new requests, only handle the established one
            handle_request(client_connection)
            client_connection.close() # Decrements descriptor reference count, not closing the connection completely, only removing the child connection
            os._exit(0)  # child exits here
        else:  # parent
            client_connection.close()  # close parent copy and loop over

if __name__ == '__main__':
    serve()
