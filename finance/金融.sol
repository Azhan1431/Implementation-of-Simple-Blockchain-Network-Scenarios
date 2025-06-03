// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title Simple Financial Ledger Contract
contract FinancialLedger {
    mapping(address => uint256) public balances;

    event Transfer(address indexed from, address indexed to, uint256 amount);
    event Mint(address indexed to, uint256 amount);
    event Burn(address indexed from, uint256 amount);

    address private _owner;

    constructor(uint256 initialSupply) {
        _owner = msg.sender;
        balances[msg.sender] = initialSupply;
        emit Mint(msg.sender, initialSupply);
    }

    function owner() public view returns (address) {
        return _owner;
    }

    function balanceOf(address account) public view returns (uint256) {
        return balances[account];
    }

    function transfer(address to, uint256 amount) public returns (bool) {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        require(to != address(0), "Invalid recipient");
        balances[msg.sender] -= amount;
        balances[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function mint(address to, uint256 amount) public returns (bool) {
        require(msg.sender == _owner, "Only owner can mint");
        balances[to] += amount;
        emit Mint(to, amount);
        return true;
    }

    function burn(address from, uint256 amount) public returns (bool) {
        require(msg.sender == _owner, "Only owner can burn");
        require(balances[from] >= amount, "Burn amount exceeds balance");
        balances[from] -= amount;
        emit Burn(from, amount);
        return true;
    }
}