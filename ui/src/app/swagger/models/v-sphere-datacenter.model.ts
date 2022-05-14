export class VSphereDatacenter {
    public name: string;
    public moid: string;

    constructor(name: string, moid: string) {
        this.name = name;
        this.moid = moid;
    }
}
