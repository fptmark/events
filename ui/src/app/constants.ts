export class Constants {
    private static _idField: string = '_id';    // Used for Mongo by default

    static get idField(): string {
        return Constants._idField;
    }
}