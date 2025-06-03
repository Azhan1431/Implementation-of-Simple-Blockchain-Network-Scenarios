// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CopyrightRegistry {
    struct Work {
        address author;
        string workHash;
        uint256 timestamp;
    }

    mapping(string => Work) public works;

    event WorkRegistered(address indexed author, string workHash, uint256 timestamp);

    function registerWork(string memory workHash) public {
        require(bytes(workHash).length > 0, "work hash required");
        require(works[workHash].timestamp == 0, "work already registered");

        works[workHash] = Work({
            author: msg.sender,
            workHash: workHash,
            timestamp: block.timestamp
        });

        emit WorkRegistered(msg.sender, workHash, block.timestamp);
    }

    function getWork(string memory workHash) public view returns (address, string memory, uint256) {
        Work memory w = works[workHash];
        require(w.timestamp != 0, "work not found");
        return (w.author, w.workHash, w.timestamp);
    }
}