import { Component, OnInit } from '@angular/core';
import { AccountService, Account } from '../../services/account.service';
import { UserService, User } from '../../services/user.service';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-account-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <h2>Accounts</h2>
    <ul>
      <li *ngFor="let account of accounts; let i = index">
        {{ i + 1 }}: Account ID: {{ account.id }}
        <ul>
          <li *ngFor="let user of accountUsers[account.id]">
            {{ user.username }} ({{ user.email }})
          </li>
        </ul>
      </li>
    </ul>
  `
})
export class AccountListComponent implements OnInit {
  accounts: Account[] = [];
  accountUsers: { [key: string]: User[] } = {};

  constructor(private accountService: AccountService, private userService: UserService) {}

  ngOnInit(): void {
    this.loadAccounts();
  }

  loadAccounts() {
    this.accountService.getAccounts().subscribe(accounts => {
      this.accounts = accounts;
      accounts.forEach(account => {
        this.userService.getUsers().subscribe(users => {
          this.accountUsers[account.id!] = users.filter(u => u.accountId === account.id);
        });
      });
    });
  }
}
