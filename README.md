# Book Swap DBMS

A database-driven system that supports peer-to-peer book exchanges using a structured relational database. The project demonstrates DBMS concepts through an ER diagram, relational schema, and SQL-based operations for managing users, books, swap requests, messages, and reviews.

## Project Overview

Book Swap DBMS enables users to list books, request swaps, communicate with other users, and provide post-swap reviews. The system uses core database design principles to ensure data integrity, consistency, and a complete record of all interactions.

## Key Features

- User account management
- Book listing and ownership tracking
- Swap request creation, approval, rejection, and status updates
- Messaging between users regarding swap details
- Review and rating system for completed swaps
- Fully relational schema ensuring traceability and consistency

## ER Diagram Summary

Core entities:
- Users
- Books
- SwapRequests
- Messages
- Reviews

Relationships:
- One user can own multiple books
- Books can receive many swap requests
- Swap requests can have multiple messages
- Books and users can have multiple reviews

## Database Design

### Entities
User(UserID, Name, Email, Phone, Address)  
Book(BookID, Title, Author, Genre, OwnerID)  
SwapRequest(RequestID, RequesterID, OwnerID, BookID, Status, RequestDate)  
Message(MessageID, SenderID, ReceiverID, RequestID, Content, Timestamp)  
Review(ReviewID, UserID, BookID, Rating, Feedback, Date)

### Example Table Creation
CREATE TABLE Users (
    UserID INT PRIMARY KEY,
    Name VARCHAR(50),
    Email VARCHAR(100),
    Phone VARCHAR(15),
    Address VARCHAR(150)
);

CREATE TABLE Books (
    BookID INT PRIMARY KEY,
    Title VARCHAR(100),
    Author VARCHAR(100),
    Genre VARCHAR(50),
    OwnerID INT,
    FOREIGN KEY (OwnerID) REFERENCES Users(UserID)
);

## Sample SQL Operations

### Insert Book
INSERT INTO Books(BookID, Title, Author, Genre, OwnerID)
VALUES (1, 'Atomic Habits', 'James Clear', 'Self-help', 101);

### Create Swap Request
INSERT INTO SwapRequest(RequestID, RequesterID, OwnerID, BookID, Status)
VALUES (2001, 101, 102, 1, 'Pending');

## What This Project Demonstrates

- ER modeling and translation to relational schema
- Keys, foreign keys, and constraints for data integrity
- Normalization up to 3NF
- SQL CRUD operations and transaction handling
- Real-world DBMS application design

## Project Structure
ER_Diagram.png  
Schema.sql  
Sample_Queries.sql  
README.md

## Contributors
Naveen Babu M S
Kishore B  
Koushal Reddy M    
Sai Charan M
