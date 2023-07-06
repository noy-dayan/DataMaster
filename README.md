![datamaster-logo](assets/loge_sideway.png)

DataMaster is a client-server software with a graphical user interface (GUI) that enables users to interact with a database. The client provides a user-friendly interface for adding, deleting, and retrieving information from tables and records. The server communicates with the database the database and processes user requests, returning the requested data to the clients.

## Features

## Technologies and Modules Used

## Code Architecture
The product consists of the following main code files, including two versions: one implemented using TCP (Transmission Control Protocol) and the other using RUDP (Reliable User Datagram Protocol).

- **AppServer.py : [TCP](AppServer_TCP.py) | [RUDP](AppServer_RUDP.py)**
  - Acts as the central hub for routing information within the system.
  - Enables communication with the clients and the database.
    
- **ClientSocket.py : [TCP](ClientSocket_TCP.py) | [RUDP](ClientSocket_RUDP.py)**
  - Handles the sending and receiving of data packets to and from the server.
  
- **Client.py : [TCP](Client_TCP.py) | [RUDP](Client_RUDP.py)**
  - Provides a graphical interface for users to interact with the software.
  - Displays relevant information to the user and handles user input.
    
- **DataBase.py : [TCP & RUDP](DataBase.py)**
  - Responsible for retrieving and storing data in the database.
  - Manages queries and updates to ensure data integrity.
  
## RUDP Functionality (WIP)


## Contact
If you have any questions, suggestions, or feedback, please feel free to contact me:
[@noy-dayan](https://www.github.com/noy-dayan)
