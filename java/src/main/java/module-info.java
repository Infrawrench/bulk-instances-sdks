/** AWS EC2 instance attributes and pricing, with full history, from Infrawrench. */
module com.infrawrench.bulkinstances {
    requires java.net.http;
    requires com.fasterxml.jackson.core;
    requires org.tukaani.xz;

    exports com.infrawrench.bulkinstances;
}
