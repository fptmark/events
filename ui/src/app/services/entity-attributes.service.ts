import { Injectable } from '@angular/core';

  export interface EntityAttributes{
        title: string;
        description: string;
        buttonLabel: string;
        operations: string;
  }

  @Injectable({
    providedIn: 'root'
  })

  export class EntityAttributesService {
    public entityAttributes: { [key: string]: EntityAttributes } = {
        account: {
            title: 'Accounts',
            description: 'Manage Accounts',
            buttonLabel: 'Manage Accounts',
            operations: 'crud'
        },
        user: {
            title: 'Users',
            description: 'Manage User Profiles',
            buttonLabel: 'Manage Users',
            operations: 'crud'
        },
        profile: {
            title: 'Profiles',
            description: 'Manage User preferences and settings',
            buttonLabel: 'Manage Profiles',
            operations: 'crud'
        },
        tagaffinity: {
            title: 'Tag Affinity',
            description: 'Manage Interest categories',
            buttonLabel: 'Manage Tag Affinities',
            operations: 'crud'
        },
        event: {
            title: 'Events',
            description: 'Manage Events',
            buttonLabel: 'Manage Events',
            operations: 'crud'
        },
        userevent: {
            title: 'User Events',
            description: 'Manage User Events and Attendance',
            buttonLabel: 'Manager User Events',
            operations: 'crud'
        },
        url: {
            title: 'URLs',
            description: 'Manage Web Sites to crawl',
            buttonLabel: 'Manage URLs',
            operations: 'crud'
        },
        crawl: {
            title: 'Crawls',
            description: 'Review Crawl results',
            buttonLabel: 'Manage Crawls',
            operations: 'rud'
        }
    };

    getTitle(entity: string){
        return this.entityAttributes[entity].title
    }

    getDescription(entity: string){
        return this.entityAttributes[entity].description
    }

    getButtonLabel(entity: string){
        return this.entityAttributes[entity].buttonLabel
    }

    getOperations(entity: string){
        return this.entityAttributes[entity].operations
    }

    constructor() {}
}
