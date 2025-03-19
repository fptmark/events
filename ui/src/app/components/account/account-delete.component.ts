import { Component, OnInit } from '@angular/core';
import { AccountService, Account } from '../../services/account.service';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-account-delete',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <h2>Delete Account</h2>
    <ul>
      <li *ngFor="let account of accounts; let i = index">
        {{ i + 1 }}: Account ID: {{ account.id }}
      </li>
    </ul>
    <input [(ngModel)]="selection" placeholder="Enter number or range (e.g. 1 or 1-2)" />
    <button (click)="deleteAccounts()">Delete Selected</button>
  `
})
export class AccountDeleteComponent implements OnInit {
  accounts: Account[] = [];
  selection: string = '';

  constructor(private accountService: AccountService) {}

  ngOnInit(): void {
    this.accountService.getAccounts().subscribe(accounts => this.accounts = accounts);
  }

  deleteAccounts() {
    let indices: number[] = [];
    if (this.selection.includes('-')) {
      const [start, end] = this.selection.split('-').map(s => parseInt(s, 10));
      for (let i = start; i <= end; i++) {
        indices.push(i);
      }
    } else {
      indices.push(parseInt(this.selection, 10));
    }

    indices.forEach(index => {
      const account = this.accounts[index - 1];
      if (account && confirm(`Delete account ${account.id} and all its users?`)) {
        this.accountService.deleteAccount(account.id!).subscribe(() => {
          alert(`Account ${account.id} deleted.`);
          this.ngOnInit();
        });
      }
    });
  }
}
