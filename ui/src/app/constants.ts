export class Constants {
    private static _idField: string = '_id';    // Used for Mongo by default

    static get idField(): string {
        return Constants._idField;
    }

    // Entity operation button colors - for reference and documentation
    static readonly BUTTON_COLORS = {
        CREATE: '#28a745', // Green
        VIEW: '#17a2b8',   // Light blue
        EDIT: '#007bff',   // Dark blue
        DELETE: '#dc3545'  // Red
    };
}